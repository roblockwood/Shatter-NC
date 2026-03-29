import { Injectable, OnModuleInit } from '@nestjs/common';
import * as http from 'http';
import * as https from 'https';
import { Logger } from 'nestjs-pino';

@Injectable()
export class WarmupService implements OnModuleInit {
  constructor(private readonly logger: Logger) {}

  async onModuleInit() {
    await this.waitForDownstreamServer();
    this.logger.log('Compressor is available. Continuing application startup.');
  }

  private async waitForDownstreamServer(): Promise<void> {
    let isServerAvailable = false;

    while (!isServerAvailable) {
      try {
        await this.pingDownstreamServer();
        isServerAvailable = true;
      } catch (error) {
        const detail =
          error instanceof Error ? error.message : String(error);
        this.logger.error(
          `Compressor is not available (${detail}). Retrying in 10 seconds.`,
        );
        await new Promise((resolve) => setTimeout(resolve, 10000));
      }
    }
  }

  /**
   * Kaeser Connect is normally HTTPS on 443. The stock code used HTTP:80 only,
   * which never succeeds on real SC2 controllers and blocked Nest from binding :3004.
   */
  private pingDownstreamServer(): Promise<void> {
    return new Promise((resolve, reject) => {
      const raw = (process.env.KAESER_ADDRESS || '').trim();
      if (!raw) {
        reject(new Error('KAESER_ADDRESS is not set'));
        return;
      }

      let url: URL;
      try {
        url = new URL(raw.includes('://') ? raw : `https://${raw}`);
      } catch {
        reject(new Error(`Invalid KAESER_ADDRESS: ${raw}`));
        return;
      }

      const isHttps = url.protocol === 'https:';
      const port = url.port
        ? parseInt(url.port, 10)
        : isHttps
          ? 443
          : 80;

      const lib = isHttps ? https : http;
      const path = '/login.html';

      const requestOptions: http.RequestOptions = {
        hostname: url.hostname,
        port,
        path,
        method: 'GET',
        timeout: 15000,
        ...(isHttps ? { rejectUnauthorized: false } : {}),
      };

      const req = lib.request(requestOptions, (res) => {
        res.resume();
        const code = res.statusCode ?? 0;
        if (code >= 200 && code < 400) {
          resolve();
        } else {
          reject(
            new Error(
              `Downstream /login.html returned HTTP ${code}`,
            ),
          );
        }
      });

      req.on('error', (err: NodeJS.ErrnoException) => {
        if (
          isHttps &&
          !url.port &&
          err.code === 'ECONNREFUSED' &&
          port === 443
        ) {
          reject(
            new Error(
              `${err.message} — nothing listening on HTTPS port 443; set KAESER_ADDRESS to http://${url.hostname} if Kaeser Connect uses HTTP on port 80`,
            ),
          );
          return;
        }
        reject(err);
      });
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Downstream request timeout (15s)'));
      });

      req.end();
    });
  }
}
