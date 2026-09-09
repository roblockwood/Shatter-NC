(O8099 - SHATTER PROBE GATE)
(260605 * SHATTER REMOTE PROBING GATE)
(Remote probing may ONLY MEMSTRT this program.)
(Shatter writes job macros then sets #908 = target O-number.)
(------------------------------------------------)
(BEFORE M0: no probe motion — review parameters)
(  #908 = TARGET PROGRAM  e.g. 8110 / 8216 / 8100)
(  #900 = WCS)
(  #901 = X DIST   #902 = Y DIST   #903 = Z DIST)
(  #904 = SIZE     #905 = CLR/ANG1 #906 = ANG2 #907 = ANG3)
(  #920 = TOOL (tool-length path only))
(AFTER M0: Cycle Start continues into M98 of #908)
(------------------------------------------------)

IF[#908EQ#0]GOTO900
IF[#908EQ0]GOTO900
IF[#908LT8000]GOTO910
IF[#908GT8999]GOTO910

(Values on MACRO page / Shatter UI — no motion until Cycle Start past M0)
#3006=(SHATTER GATE: REVIEW #908+#900-920)
M0

(Operator confirmed — call selected helper under /PROGRAM)
M98P#908

M30

N900
#3000=909(NO_TARGET_PROGRAM_IN_908)
M30

N910
#3000=910(TARGET_#908_OUT_OF_RANGE)
M30
