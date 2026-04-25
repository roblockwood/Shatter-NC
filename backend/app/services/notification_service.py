"""Notification service for delivering machine status alerts via email/SMTP and SMS."""
import asyncio
import logging
import re
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Optional
from zoneinfo import ZoneInfo

import aiosmtplib

from app.core.config import settings
from app.db.base import SessionLocal
from app.models.notification import NotificationChannel, NotificationLog, NotificationRule

logger = logging.getLogger(__name__)

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


def _normalize_alarm_code(code: Any) -> str:
    """Normalize alarm code strings for robust rule matching."""
    if code is None:
        return ""
    raw = str(code).upper().strip()
    # Keep only alphanumerics so values like "OM0500]" still match "OM0500".
    return re.sub(r"[^A-Z0-9]", "", raw)


def _format_runtime_hms(duration_seconds: Optional[int]) -> str:
    """Format elapsed runtime as HH:MM:SS."""
    if duration_seconds is None:
        return ""
    total_seconds = max(0, int(duration_seconds))
    hours, rem = divmod(total_seconds, 3600)
    mins, secs = divmod(rem, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"


def _format_pacific_time(value: Optional[datetime]) -> str:
    """Render a timestamp in Pacific time as DD-MMM-YY HH:MM TZ."""
    if value is None:
        return ""

    aware_value = value
    if aware_value.tzinfo is None:
        # Polling persists UTC with datetime.utcnow(); treat naive values as UTC.
        aware_value = aware_value.replace(tzinfo=timezone.utc)

    pacific_dt = aware_value.astimezone(PACIFIC_TZ)
    return pacific_dt.strftime("%d-%b-%y %H:%M %Z").upper()


class NotificationService:
    """Delivers notifications via configured channels when machine status rules match."""

    async def start(self) -> None:
        logger.info("NotificationService started")

    async def stop(self) -> None:
        logger.info("NotificationService stopped")

    async def notify_status_change(
        self,
        machine_id: int,
        machine_name: str,
        previous_status: Optional[str],
        new_status: str,
        alarms: list[dict] = [],
    ) -> None:
        if previous_status == new_status:
            return

        # Cycle-complete transitions should use notify_cycle_complete formatting.
        if previous_status == "operating" and new_status in ["standby", "stopped"]:
            return

        subject_prefix = "[ALARM]" if new_status == "error" else "[STATUS]"
        subject = f"{subject_prefix} {machine_name}: {previous_status} → {new_status}"

        lines = [f"Machine: {machine_name}", f"Status change: {previous_status} → {new_status}"]
        if new_status == "error" and alarms:
            lines.append("")
            lines.append("Active alarms:")
            for alarm in alarms:
                code = alarm.get("code", "")
                # Prefer databank-enriched description for the machine control version.
                msg = alarm.get("description") or alarm.get("message", "")
                severity = alarm.get("severity", "")
                lines.append(f"  [{code}] {msg}" + (f" ({severity})" if severity else ""))
                cause = alarm.get("cause", "")
                solution = alarm.get("solution", "")
                if cause:
                    lines.append(f"     Cause: {cause}")
                if solution:
                    lines.append(f"     Solution: {solution}")

        body = "\n".join(lines)
        await self._dispatch_to_matching_rules(
            machine_id=machine_id,
            previous_status=previous_status,
            new_status=new_status,
            subject=subject,
            body=body,
            event_type="status_change",
            event_data={"previous_status": previous_status, "new_status": new_status, "alarms": alarms},
        )

    async def notify_cycle_complete(
        self,
        machine_id: int,
        machine_name: str,
        program_name: Optional[str],
        duration_seconds: Optional[int],
        o_number: Optional[str] = None,
        started_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
        new_status: str = "stopped",
    ) -> None:
        duration_hms = _format_runtime_hms(duration_seconds)
        start_time_local = _format_pacific_time(started_at)
        stop_time_local = _format_pacific_time(ended_at)

        subject = f"[CYCLE COMPLETE] {machine_name}"
        lines = [
            f"[CYCLE COMPLETE] {machine_name}",
            f"Program: {program_name or '(unknown)'}",
        ]
        if stop_time_local:
            lines.append(f"Stop Time: {stop_time_local}")
        if duration_hms:
            lines.append(f"Total Runtime: {duration_hms}")
        if start_time_local:
            lines.append(f"Start Time: {start_time_local}")
        if ended_at and not stop_time_local:
            lines.append(f"Ended: {ended_at.isoformat()}")

        body = "\n".join(lines)
        await self._dispatch_to_matching_rules(
            machine_id=machine_id,
            previous_status="operating",
            new_status=new_status,
            subject=subject,
            body=body,
            event_type="cycle_complete",
            event_data={
                "program_name": program_name,
                "o_number": o_number,
                "duration_seconds": duration_seconds,
                "duration_hms": duration_hms,
                "start_time_local": start_time_local,
                "stop_time_local": stop_time_local,
                "started_at": started_at.isoformat() if started_at else None,
                "ended_at": ended_at.isoformat() if ended_at else None,
            },
        )

    async def _dispatch_to_matching_rules(
        self,
        machine_id: int,
        previous_status: Optional[str],
        new_status: str,
        subject: str,
        body: str,
        event_type: str,
        event_data: dict[str, Any],
    ) -> None:
        db = SessionLocal()
        try:
            rules = (
                db.query(NotificationRule)
                .filter(
                    NotificationRule.enabled,
                    NotificationRule.trigger_type == "status_change",
                    (
                        (NotificationRule.machine_id == machine_id)
                        | (NotificationRule.machine_id is None)
                    ),
                )
                .all()
            )

            alarms_list = event_data.get("alarms", []) if event_data else []

            for rule in rules:
                if not self._rule_matches(rule.trigger_config, previous_status, new_status, alarms_list):
                    continue

                for channel_id in (rule.channel_ids or []):
                    channel = db.query(NotificationChannel).filter(
                        NotificationChannel.id == channel_id,
                        NotificationChannel.enabled,
                    ).first()
                    if not channel:
                        continue

                    status, error = await self._send(channel, subject, body)
                    log = NotificationLog(
                        rule_id=rule.id,
                        channel_id=channel.id,
                        machine_id=machine_id,
                        event_type=event_type,
                        event_data=event_data,
                        message=f"Subject: {subject}\n\n{body}",
                        status=status,
                        error_message=error,
                    )
                    db.add(log)

            db.commit()
        except Exception as e:
            logger.error(f"NotificationService error for machine {machine_id}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    def _rule_matches(
        self,
        trigger_config: dict,
        previous_status: Optional[str],
        new_status: str,
        alarms: Optional[list[dict]] = None,
    ) -> bool:
        if not trigger_config:
            return False
        if trigger_config.get("any"):
            return True

        to_status = trigger_config.get("to_status")
        if to_status is not None:
            if isinstance(to_status, list):
                if new_status not in to_status:
                    return False
            else:
                if new_status != to_status:
                    return False

        from_status = trigger_config.get("from_status")
        if from_status is not None and previous_status != from_status:
            return False

        # If all active alarms are in the exclusion list, suppress the notification
        exclude_codes = trigger_config.get("exclude_alarm_codes")
        if exclude_codes and alarms:
            exclude_set = {
                _normalize_alarm_code(c)
                for c in exclude_codes
                if _normalize_alarm_code(c)
            }
            active_codes = {
                _normalize_alarm_code(a.get("code", ""))
                for a in alarms
                if _normalize_alarm_code(a.get("code", ""))
            }
            if active_codes and active_codes.issubset(exclude_set):
                return False

        return True

    async def _send(self, channel: NotificationChannel, subject: str, body: str) -> tuple[str, Optional[str]]:
        try:
            if channel.channel_type == "email":
                await self._send_email(channel.config, subject, body)
                return "sent", None
            elif channel.channel_type == "sms":
                await self._send_sms(channel.config, subject, body)
                return "sent", None
            else:
                return "failed", f"Unknown channel type: {channel.channel_type}"
        except Exception as e:
            logger.warning(f"Notification send failed for channel {channel.id}: {e}")
            return "failed", str(e)

    async def _send_email(self, config: dict, subject: str, body: str) -> None:
        smtp_host = config.get("smtp_host") or settings.SMTP_HOST
        smtp_port = int(config.get("smtp_port") or settings.SMTP_PORT)
        username = config.get("username") or settings.SMTP_USERNAME
        password = config.get("password") or settings.SMTP_PASSWORD
        use_tls = bool(config.get("use_tls", settings.SMTP_USE_TLS))
        start_tls = bool(config.get("start_tls", settings.SMTP_START_TLS))
        to_address = config.get("to")
        from_address = config.get("from") or username

        if not smtp_host:
            raise ValueError("SMTP host not configured")
        if not to_address:
            raise ValueError("Recipient address not configured")

        message = EmailMessage()
        message["From"] = from_address or "shatter@localhost"
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=smtp_port,
            username=username or None,
            password=password or None,
            use_tls=use_tls,
            start_tls=start_tls,
        )

    async def _send_sms(self, config: dict, subject: str, body: str) -> None:
        account_sid = config.get("account_sid") or settings.TWILIO_ACCOUNT_SID
        auth_token = config.get("auth_token") or settings.TWILIO_AUTH_TOKEN
        from_number = config.get("from") or settings.TWILIO_FROM_NUMBER
        to_number = config.get("to")

        if not account_sid:
            raise ValueError("Twilio account SID not configured")
        if not auth_token:
            raise ValueError("Twilio auth token not configured")
        if not from_number:
            raise ValueError("Twilio from number not configured")
        if not to_number:
            raise ValueError("Recipient phone number not configured")

        sms_body = f"{subject}\n{body}"

        from twilio.rest import Client as TwilioClient

        def _send_sync() -> None:
            client = TwilioClient(account_sid, auth_token)
            client.messages.create(body=sms_body, from_=from_number, to=to_number)

        await asyncio.to_thread(_send_sync)

    async def send_test(self, channel: NotificationChannel) -> tuple[str, Optional[str]]:
        """Send a test notification via the given channel. Returns (status, error)."""
        return await self._send(
            channel,
            subject="[TEST] Shatter NC notification test",
            body="This is a test notification from Shatter NC.\n\nIf you received this, your channel is configured correctly.",
        )
