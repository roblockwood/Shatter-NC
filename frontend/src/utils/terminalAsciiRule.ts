// Copyright (C) 2024 Shatter-NC contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

/** Long clipped horizontal rule — flex + overflow hides excess; brief string would gap on ultrawide expanded panes. */
const TERMINAL_RULE_FILL_CHARS = 8000;

export const TERMINAL_RULE_FILL = '─'.repeat(TERMINAL_RULE_FILL_CHARS);
