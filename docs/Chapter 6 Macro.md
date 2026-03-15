Chapter 6 Macro


6.6 External Output Function
When executing an external output command shown below during memory operation, the macro
variable values or characters can be output to external devices through RS-232C or can be output
as a file to a memory card/FTP server.

1. POPEN … Instruction that executes a preparatory processing of data output
2. BPRNT … Instruction that executes an output of characters and a binary output of
macrovariable values
3. DPRNT ... Instruction that executes an output of characters and a character string output
of macro variable values
4. PCLOS … Instruction that executes a terminating processing of data output

Figure 1 NC program that contains the external output command

G90;
:
POPEN;
BPRNT[#100[3]];
DPRNT[#2[63]];
PCLOS;
:
M30;



6 6.6.1 POPEN
This command links with an external connection. Specify this command prior to respective
commands of BPRNT, DPRNT, and PCLOS.

Command format POPEN;

When connecting to a <General COMM device>
The control code of “DC2” is output if the <Communication mode> of the <Communication
parameter> is <1: Code 1> or <2: Code 2>.Nothing is output if <0: Line> is set.

When connecting to a <Memory card>
It opens the memory card file.

When connected to an <FTP server>
This connects to the FTP server.

(Note 1) If POPEN is specified when the POPEN state has already been
established, it is ignored.
(Note 2) When connecting to a <Memory card>, be sure to keep the memory card
inserted without removing it until the PCLOS command or the program is
finished.




2019/09/02 6 - 28 eCOM3NCPR6
Chapter 6 Macro

6.6.2 BPRNT
This command executes an output of characters and a binary output of macro variable values.

Command format BPRNT[ xx #xx [x] … ];


(Note 1) The alarm << POPEN is unable. >> occurs if BPRNT is commanded
without first commanding POPEN.
(Note 2) Add the “end of block” code at the end of output data.

1. Output of characters
The following characters are output as they are.
Alphabets “A” to “Z”
Numbers “0” to “9”
Symbols “(” “)” “=” “/” “.” “+” “,” “-” “?”

A space is not output. Instead, “###” is output with a space code.

(Note 1) When connecting to a <General COMM device>, the output character
code follows the <Communication parameter> <Send data code> setting.
The output character code does not output “?” when using EIA format.
(Note 2) The alarm <<Macro Command Error>> occurs if “#”, “[” and “]” are
output (used other than in the output format of macro variables).
(Note 3) Motion is not guaranteed when using characters that cannot be output.

2. Output of macro variables 6
Specify the number of significant digits after decimal point in square brackets following the
variable command. Macro variable value is treated as 4-byte (32-bit) data, and it is output as
binary data, starting from the high-order byte.

(Note 1) When a macro variable value is a negative value, it is output in the
expression of two’s complement.
(Note 2) If the number of digits after decimal point of the data to be output is
larger than the significant digits, the output data is rounded off.
(Note 3) The alarm << Too many external output command digit.>> occurs when
the macro variable value exceeds the range of -2147483648 to 2147483647
as a result of forms processing.

BPRNT example:

BPRNT[DATA*X*#100[2] Y*#101[2] Z*#102[0]];

Variable values are
#100=123.456
#101=-123.456
#102=0.056
When output character code is set to ISO, and the end code of the block to CR, LF

44 41 D4 41 A0 D8 A0 00 00 30 3A 59 A0 FF FF CF C6 5A A0 00 00 00 00 8D 0A
DATA SP X SP 12346 Y SP -12346 Z SP 0 CR,LF

* SP: space code




2019/09/02 6 - 29 eCOM3NCPR6
Chapter 6 Macro

6.6.3 DPRNT
This command executes an output of characters and a character string output of macro variable
values.

Command
format DPRNT [ xx #xx [x x] … ];


Significant digits after decimal point (0 to 9)

Significant digits before decimal point (0 to 9)
Macro variable
Character

(Note 1) The alarm << POPEN is unable. >> occurs if DPRNT is commanded
without first commanding POPEN.
(Note 2) Add the “end of block” code at the end of output data.

1. Output of characters
Same as the BPRNT command. Refer to 1. Output of Characters, 6.6.2 BPRNT.

2. Output of macro variables
Of a macro variable value, specify necessary number of digits before and after decimal point
respectively in square brackets. By this command, a macro variable value is output with the
6 character codes including decimal point by the amount of number of digits specified, every
digit starting from the high-order digit.

A space code is output for the high-order zero and a positive sign if the <leading zero suppression
(DPRNT)> of the <Communication parameter> is set to <0: Type 1>. Nothing is output if <1:
Type 2>.
When the number of digits after decimal point is other than 0, the decimal point and a value after
decimal point are always output. If the number of digits after decimal point is 0, the decimal point
is not output.

(Note 1) If the number of significant digits specified is 1, the number of significant
digits before decimal point is treated as 0.
(Note 2) A numerical value exceeding the number of significant digits is not
output. If the number of digits after decimal point of the data to be output
is larger than the significant digits, the output data is rounded off.
(Note 3) When the data is 0 as a result of rounding off, a sign depends on a
numeric value before it was rounded off.




2019/09/02 6 - 30 eCOM3NCPR6
Chapter 6 Macro


DPRNT example:

DPRNT[X*#100[44] Y*#101[22] Z*#102[20] *#100[2]];

Variable values are
#100=-123.456
#101=123.456
#102=0.056
When output character code is set to ISO, and the end code of the block to CR, LF

(1) <Leading zero suppression (DPRNT)> of <Communication parameter> is set to <0: Type 1>

D8 A0 2D A0 B1 B2 33 2E B4 35 36 59 A0 A0 B2 33 2E B4 36 5A A0 A0 A0 30 A0 2D 2E B4 8D 0A
30 36
X SP -SP123.4560 Y SP SP23.46 Z SP SPSP0 SP -.46 CR,LF

(2) <Leading zero suppression (DPRNT)> of <Communication parameter> is set to <1: Type 2>

D8 A0 2D B1 B2 33 2E B4 35 36 30 59 A0 B2 33 2E B4 36 5A A0 30 A0 2D 2E B4 36 8D 0A
X SP -123.4560 Y SP 23.46 Z SP 0 SP -.46 CR,LF

* SP: space code

6.6.4 PCLOS
This command cancels the link with the external connection. Specify this command after 6
respective commands of POPEN, BPRNT, and DPRNT.

Command format PCLOS;

When PCLOS is specified, if the data output by the BPRNT or DPRNT command is underway, the
PCLOS processing is executed after the data output is completed.

When connecting to a <General COMM device>
The control code of “DC4” is output if the <Communication mode> of the <Communication
parameter> is <1: Code 1> or <2: Code 2>. Nothing is output if <0: Line> is set.

When connecting to a <Memory card>
It closes the memory card file.

When connected to an <FTP server>
The connection to the FTP server is severed.

(Note) If PCLOS is specified when the PCLOS state has already been
established (including the state in which POPEN is not executed), it is
ignored.

6.6.5 External Output to Memory Card
The external output data is saved in the root folder under the file name: date + sequence number.
Output folder : Root folder
Output file name : yyyymmdd_**.log
yyyy: year mm: month dd: day
**: sequence number (00~99)

The external output file saves the output data from POPEN to PCLOS inside the program, or until
the program finishes.

A new output data file is created when an external output file with the same date does not exist in
the memory card. When an external output file with the same date exists, it is added to the file
with the largest sequence number.
When the file size exceeds 20 MB for POPEN, a file with the next available sequence number is
created and saved.


2019/09/02 6 - 31 eCOM3NCPR6
Chapter 6 Macro


A maximum of 100 external output files with the same date can be saved.
However, if a “yyyymmdd_99.log” file already exists when creating a file, the alarm <<External
output file cannot be created.>> is triggered and the file cannot be saved.
Even if there is an available number in the middle of the sequence, it is skipped over and the next
biggest number is used. As a result, even when the maximum (100) is not exceeded, the same
alarm is triggered and the file cannot be saved.
If there is not enough space available on the memory card and the file cannot be saved, the alarm
<<Memory overflow (Memory card)>> is triggered.

The data that is output to the external output file can be opened using software that supports the
following file formats.
Data output using BPRNT command: Binary format
Data output using DPRNT command: Text format

(Note) The output data is added even if the external output file attributes that
exist in the memory card are changed to reading only.

6.6.6 External Output to FTP Server
The data that is output externally is saved under the file name (character string + date + sequence
number) specified in the communication parameter <External output - FTP output name> and is
saved to the folder specified in the communication parameter <External output - FTP output
destination>.
Output folder: Folder specified in the communication parameter <External output –
FTP output destination>
6 Output folder name: SSSSSyyyymmdd_****.log
SSSSS: Character string specified in the communication parameter
<External output – FTP output name>
yyyy: Year
mm: Month
dd: Day
****: Sequence number (0000 to 9999)

The external output file uses the APPE command to save the output data from POPEN to PCLOS
inside the program, or until the program finishes.
(Note 1) A server that supports the APPE command needs to be specified for the
server used for saving.
(Note 2) This machine cannot be specified as a server for saving.

A new output data file is created when an external output file with the same date does not exist in
the <Output folder>. When an external output file with the same date exists, it is added to the file
with the largest sequence number.
When the file size exceeds 20 MB for POPEN, a file with the next available sequence number is
created and saved.

A maximum of 10000 external output files with the same date can be saved.
However, if an “SSSSSyyyymmdd_9999.log” file already exists when creating a file, the alarm
<<External output file cannot be created.>> is triggered and the file cannot be saved.
Even if there is an available number in the middle of the sequence, it is skipped over and the next
biggest number is used. As a result, even when the maximum (10000) is not exceeded, the same
alarm is triggered and the file cannot be saved.

The data that is output to the external output file can be opened using software that supports the
following file formats.
Data output using BPRNT command: Binary format
Data output using DPRNT command: Text format

When there are a lot of files inside the output folder, it may take some time to process them.
In addition, it may take some time for a reply depending on the server and network configuration.
Therefore, we recommend using a high speed server and network when possible.




2019/09/02 6 - 32 eCOM3NCPR6
Chapter 6 Macro

6.6.7 Precautions for External Output Command
(Note 1) External output commands are used in memory operation (including
extended memory operation) of NC langquage. The alarm <<Macro
Command Error>> occurs when external output commands are issued in
MDI and tape operation.
(Note 2) Data is output also in dry run and machine lock.
(Note 3) The mode cannot be changed when executing an external output
command.
(Note 4) At program restart, external output commands specified before the
restart position are also executed.
(Note 5) Variables that are empty are regarded as 0.
(Note 6) Up to 10 macro variables may be specified in the output data of one
block.
(Note 7) It is not possible to specify macro variables and the number of significant
digits using a macro variable.

BPRNT[#[#100][1]];

DPRNT[#100[#1]];

(Note 8) If the following operations are performed before the PCLOS command is
executed, the communication is blocked without carrying out the PCLOS
processing when connected to a <General COMM device>.When
connected to an <FTP server> and a PCLOS command is processed, the
connection to the FTP server is severed. 6
When connecting to a <General COMM device>
• [RST] key is pressed
• Operation is reset (except operation reset by M30)
When connecting to a <Memory card>
• [RST] key is pressed
• Operation reset
• Running program is stopped due to alarm (stop level 3 or higher)
• Running program is stopped when alarm (stop level 2 or higher) is
triggered
When connected to an <FTP server>
• [RST] key is pressed
• Operation reset
• Running program is stopped due to alarm (stop level 3 or higher)
• Running program is stopped when alarm (stop level 2 or higher) is
triggered

(Note 9) When connected to a <General COMM device>, if the <Communication
parameter> <Check DR signal> is set to <1: Yes>, the DR signal is
checked between the POPEN command until the PCLOS command. The
alarm <<DR signal off>> occurs when DR signals are turned off during
this period.
(Note 10) When connected to a <General COMM device>, a <Memory card> or an
<FTP server> and another setting is configured, the alarm <<Connected
to wrong device>> is triggered when the POPEN command is executed.




2019/09/02 6 - 33 eCOM3NCPR6
Chapter 6 Macro


6.7 Interrupt Macro (Option)
Interrupt macro is a function to suspend the program currently being executed on detecting an
interrupt signal (external input signal: UINT) and execute the commanded program.
A program that is executed by interruption is called interrupt program.

Command format M96 P_;

P : Interrupt program No.

Use the command below to cancel an interruption.

Command format M97;


The following conditions are required to use interrupt macros:
・ The system is in the memory operation mode
・ The system is in automatic operation (external output: STL signals ON)
・ Not executing an interrupt macro
Any interrupt signal that is received under conditions other than the above is ignored.

Subprograms and macros can be called from interrupt programs.

Insert M99 command to return from an interrupt macro to the main program. The sequence
number in the main program to return to can be specifed using P address.
6 In addition to use of M97, the following operations cancel interruption:
・ Operation reset
・ Commanding M02 (M30)
M97 is effectively commanded in an interrupt program or in a program called from an interrupt
program.


Main program Interrupt

(O0001) (O1000)
Interrupt
signal
M96 P1000; → ignored
Interrupt signal

Interrupt signal is Without P command
accepted in this period
M99(P0200);

M97;

With P command
Interrupt signal is not
accepted hereafter

Interrupt
N0200;
signal
→ ignored

M30;




2019/09/02 6 - 34 eCOM3NCPR6
Chapter 6 Macro

(Note 1) The alarm <<Invalid command>> occurs when other G / M code is
commanded in the blocks of M96 / M97.
Axes will not move if you command X, Y, and Z axes.
(Note 2) If P command is absent in an M96 command block, the<<Subprogram
number error>> occurs. If a non-existent program number is designated,
<<No subprogram>> occurs.
(Note 3) When an interrupt signal is detected during execution of a subprogram,
the interrupt program is called.

Interrupt
(O0001) (O2000) signal
(O1000)

M96 P1000;

M98 P2000;

M30; M99; M99;


(Note 4) The alarm <<Interrupted program call error>> occurs at the time of calling
an interrupt program when an interrupt signal is detected during
execution by G65/G66/M98 of subprogram specified as interrupt program.


(O0001) (O1000) Interrupt signal


M96 P1000;
Alarm <<Interrupted program call
error>> occurs
6
M98 P1000;

M30; M99;


(Note 5) The alarm <<Interrupted program call error>> occurs at the time of calling
an interrupt program when an interrupt signal is detected during
execution of a subprogram which parent program is the subprogram
specified in the interrupt program.
Interrupt signal

(O0001) (O1000) (O1001)
Alarm <<Interrupted
M96 P1000; program call error>>
M98 P1001; occurs
M98 P1000;

M30; M99; M99;


(Note 6) The alarm <<Subprogram call error>> occurs when calling the parent
program from an interrupt program which has been called during
execution of a subprogram.

Interrupt
(O0001) (O1001) signal (O1000) Alarm <<Subprogram
call error>> occurs
M96 P1000;
M98 P1001;
M98 P1001;

M30; M99; M99;




2019/09/02 6 - 35 eCOM3NCPR6
Chapter 6 Macro

(Note 7) When the total program size that is loaded (including the interrupt
program size) exceeds the size that is set in the user parameter (switch 1)
<Program load size>, the machine operates in the extended memory
operation mode. In this mode, the operation may stop for a time period
equivalent to the time required for loading if the size of the interrupt
program is large.
(Note 8) You may specify the interrupt program number using macro variables.
Refer to 8.3 Simple Call Function, Chapter 8 Subprogram Function.

6.7.1 Interrupt Type
<Interrupt type macro interrupt system> of <User parameter> is used to set how to interrupt a
block currently being executed on detecting an interruption signal.

1. Type 1: Interrupt by suspending the execution
The currently being executed block is suspended on detecting an interrupt signal, and the
interrupt program starts immediately.

When NC statements are included in the interrupt program or subprogram / macro program
called from the interrupt program, the commands included in the interrupted block are lost,
and the source program re-starts from the block next to the affected block on returning to the
source program.

Interrupt signal ON Suspended due
to interrupt


6
Ordinary program
This portion not executed


Interrupt program
NC statement exists


In the absence of NC statements, the commands in the suspended block continue on returning
to the source program.


Interrupt signal ON Suspended due
to interrupt




Ordinary program
Remainder executed


Interrupt program
No NC statement



Refer to “6.7.6.Macro Statement and NC Statement” for the detailed description of NC
statement.

2. Type 2: Interrupt without suspending the execution
The interrupt program is executed on detecting an interrupt signal without suspending the
currently executed block.

Macro statements up to the first NC statement in the interrupt program or subprogram / macro
program called from the interrupt program are processed in parallel with the currently
executed block.
Timing of start of processing of macro statements may differ depending on the contents of the
currently executed block.




2019/09/02 6 - 36 eCOM3NCPR6
Chapter 6 Macro

• Currently executed block is a single operation command:
Macro statement is executed immediately.
Interrupt sig. ON
N2 Ex.: G1X-100.;




Ordinary program



Interrupt program
Execute macro Execute NC statement
statement only


• Currently executed block is a multiple operation command:
Macro statement is executed simultaneously with the last travel command of the cycle
operation.

Start of last travel command of G28.
Interrupt signal ON (Travel command to reference point)

N2 Ex.:G91 G28 X0.;



Ordinary program

6
Interrupt program Execute macro
statement only Execute NC statement


Multiple operation commands are listed below. All other commands are single operation
commands.
• Reference point return (G28/G29/G30)
• Canned cycle (G73 to G89, G177 to G189)
• Tool replacement canned cycle (G100/M06)
• Coordinate calculation function (G36 to G39)

For both types of interruption, blocks after the first NC statement are executed after completion of
the currently executed block.

Refer to 6.7.6 Macro Statement and NC Statement for the detailed description of NC and macro
statements.

(Note) Operation of “Type 2: Interrupt without suspending the execution”
applies, irrespective of the value of <Interrupt type macro interrupt
system>, when the following operations are currently executed:
• Reference point return (G28/G29/G30)
• Canned cycle (G73 to G89, G177 to G189)
• Tool replacement canned cycle (G100/M06)
• Pallet turn
• Coordinate calculation function (G36 to G39)
• Automatic workpiece measurement (G120 to G129)
• Tap torsion direction change (G133/G134)




2019/09/02 6 - 37 eCOM3NCPR6
Chapter 6 Macro

6.7.2 Call Type
There are two types of calling an interrupt program in interrupt macros. One of them is selected in
the <Interrupt type macro call system> of <User parameter>.

1. Subprogram type interruption
Interrupt programs are called as subprogram. The level of local variables will not change
before and after interruption.

2. Macro type interruption
Interrupt programs are called as macro program. The level of local variables will change
before and after interruption. It is not possible, however, to deliver arguments from the
program currently being executed. All local variables immediately after interruption are
cleared to <empty.>

In either type of call, the call does not increase multiplicity of subprogram / macro call.
Subprogram / macro call conducted in an interrupt program increases respective multiplicity.

6.7.3 Acceptance Type
There are two interrupt signal acceptance types. One of them is set with the <Interrupt type macro
reception system> of <User parameter>.

1. Type 1: Status trigger system
Signals are accepted when interrupt signal is ON.
An interrupt program is executed when the interrupt signal is ON at the time when the
interrupt macro becomes valid with M96.
6 An interrupt program can be repeatedly executed if you keep the interrupt signal ON steadily.

2. Type 2: Edge trigger system
Signals are accepted only at the timing of interrupt signal rising from OFF to ON. Interrupt
program is not executed even when the interrupt signal is ON at the time when an interrupt
macro becomes valid with M96.


Interrupt signal
ON


OFF


Status trigger system




Edge trigger system Execute interrupt macro




2019/09/02 6 - 38 eCOM3NCPR6
Chapter 6 Macro

6.7.4 Interrupt Macro and Modal Information
The modal information, changed in the interrupt program, is differnetly transferred to the source
program depending on how the control leaves the interrupt program.

1. Returning with M99 (sequence number not specified)
Modal information except M code (G/T/H/D/S/F codes) before interruption is valid. Modal
information modified in the interrupt program turns invalid.

M code modal information, modified in the interrupt program, continues to be valid as it is
modified.
Main program Interrupt program

(O0001) (O1000)
M96 P1000; G91
G90 M05;
M03 S1000
Interrupt signal

Without P
command



Modal before
interrupt restores
except M code
modal
M99;
6
2. Returning with M99PXXXX (with a sequence number specified)
Modal information, modified in the interrupt program, is valid as it is modified.
You can reference the modal information used before interruption using system variables
#4401 to #4530.

Main program Interrupt program

(O0001) (O1000)
Interrupt signal M96 P1000;




N0200;
With P
command
Modal as modified in
interrupt program is valid
M99 P0200;




2019/09/02 6 - 39 eCOM3NCPR6
Chapter 6 Macro

6.7.5 Interrupt Macro and Current Position
The values of macro variables indicating the current position at execution of an interrupt program
are shown below.

Interrupt occurs B0

Tool center path B1


A0




Program path


Variable No. Contents Conditions of reference Coordinate values
#5001 to End point From interruption to the first It is undefined. Do not
#5008 coordinates NC statement use it.
After start of NC statement that Coordinates of B1
does not include travel position
commands
After start of NC statement that Coordinates of end
include travel commands point of travel
command
#5021 to Current position Machine coordinates of
6 #5034 (Machine coordinate B1 position
system)
#5041 to Current position Workpiece coordinates
#5054 (Workpiece of B1 position
coordinate system)

Refer to the “6.7.6 Macro Statement and NC Statement” for the detailed description of NC
statement.

6.7.6 Macro Statement and NC Statement
Blocks satisfying the conditions below are macro statement. Those that do not satisfy them are NC
statement.

• Includes calculation command (Refer to “6.3 Calculation function”) (*)
• Includes control command (Refer to “6.4 Control function”) (*)
• Includes external output command (Refer to “6.6 External output function”) (*)
• Includes macro simple call command (G65)
• Includes subprogram call command (M98)
• Includes a return command (M99) from macro program / subprogram

* Only when <User parameter> <Macro command single stop> is selected to <0: No>.

Blocks that do not conduct Single Block Stop in single operation may be said macro statement and
those that do conduct Single Block Stop NC statement.




2019/09/02 6 - 40 eCOM3NCPR6
Chapter 6 Macro

6.7.7 Restrictions
1. The alarm <<Specified G code cannot be used>> occurs when interrupting in the
programmable mirror image (G51.1), rotational transformation (G68), or scaling (G51) mode
and commanding the same programmable mirror image (G51.1), rotational transformation
(G68), or scaling (G51) again in the interrupt program.

2. When <Interrupt macro interrupt type> is set to type 2 and macro program modal call (G66)
and interrupt type macro (M96) are modals, if an interrupt signal is detected during a travel
axis command, the interrupt type macro (M96) is given priority and called. The registered
macro program will not be called in the modal call (G66).

3. Macro modal call (G66) is canceled on calling an interrupt program. G66 must be commanded
in the interrupt program if you wish to perform macro modal call in the interrupt program.

4. The interrupt program is executed after finishing search when an interrupt signal is detected
during search of sequence number of GOTO instruction, END instruction of WHILE – END,
and sequence number of M98Hxxxx and M99Pxxxx.

5. Interrupt signals, which are detected during search of the block specified by program restart
(Sequence Search), are ignored.

6. Interrupt signals, which are detected during search of the block specified by program restart
(Restart) and during return operation, are ignored.

7. When an interrupt signal is detected during a dwell, the interrupt program is executed after the
dwell. 6
8. When an interrupt signal is detected while waiting for ON/OFF of BCD signal output and M
signals of M460, etc., the interrupt program is executed after detecting ON/OFF of the waiting
signal.

9. The alarm << High accuracy A (or B) invalid command >> occurs when commanding M96 in
the high accuracy mode. The alarm << High accuracy A (or B) invalid modal>> occurs when
commanding a high accuracy mode (M260 / M261 / M262 / M265) in the M96 modal.

10. When an NC statement is included in the interrupt program or subprogram / macro program
called from an interrupt program, the M99 command block for returning from the interrupt
program to the original program will perform single block stop in the case of single operation.

11. When the door opens for safety reasons, the interrupt type macro function does not enable.
Refer to “Door Interlock” in the Operation Manual (Operation) for further details on door
open definition.

12. The following operations do not apply: mirror image, scaling, rotational transformation, cutter
compensation and nose R compensation, when performing axis travel for an interrupt program,
and within a sub program / macro program that is called from an interrupt program.

13. It returns to the original path from the second travel operation after the return operation when
an interrupt occurs during a cutter compensation operation and nose R compensation operation
and when there is an NC statement in the interrupt program, and within a sub program / macro
program that is called from an interrupt program.

(Note) During cutter compensation when an interference check is being
carried out for nose R compensation, the interference check starts
again at the place where it returns to the original path.

14. When the item <Interrupt type macro interrupt system> is set to <0: Type 1> (interrupts by
cancelling execution), if travel for tool length offset and for tool position compensation is lost
due to the interruption, compensation will not be executed until the next Z-axis travel
operation, and until the next X-, Y- and Z-axes travel operation.




2019/09/02 6 - 41 eCOM3NCPR6
Chapter 6 Macro


15. Even if the following keys are pressed: [MANU], [MDI] and [EDIT] between the time when
the interrupt signal is detected until the end when the interrupt program is executed with M99,
the alarm <<Interrupt type macro execution is being prepared>> is displayed and the mode
cannot be changed.

16. The alarm <<Interrupt type macro post-process being executed>> occurs and the mode will
not change if you press [MANU], [MDI], or [EDIT] key during the time between completion
of interrupt program and return to the original program.

17. When restoring from the interrupt program during extension memory operation/tape operation,
the sequence number cannot be specified.
If an instruction is given, an <<Invalid command>> alarm will occur.

18. If an interrupt occurs during incremental mode (G91) and an NC sentence exists in the
interrupt program or a sub-program or macro program which is called from the interrupt
program, the first movement command given after the reset will be treated as an incremental
command from the coordinates where the reset occurred.

19. When the command M96 is issued inside the following sub program or macro program, the
alarm <<Interrupt type macro command not possible>> is triggered. If extension or tape
operation is used, the alarm <<Specified M code cannot be used>> is triggered.
• Macro program that is called using G code (or M code).
• Sub program / macro program that is called using the command M98, G65 or G66 from a
macro program that is called using G code (or M code).
6 20. When an interrupt signal (UINT) is detected inside the macro program that is called using G
code (or M code), it interrupts and executed the program that is specified in the M96
command.

21. The alarm <<Feature coordinate manufacturing mode engaged>> is triggered when an M96
command is issued while in feature coordinate manufacturing mode. In addition, the alarm
<<Feature coordinate command error>> is triggered when a feature coordinate setting
command (G68.2) is issued during M96 modal.

6.7.8 Reference Folder When Interrupt Type Macro is
Executed
The folder that is referenced when executing an interrupt type macro is as follows depending on
the operation type.
Operation type Reference folder
Internal memory operation Same folder as the main program
Tape operation Root folder in the NC memory

(Note 1) The folder is the same one that is referenced when executing the M98
command.
(Note 2) The folders above are referenced as well when an interrupt signal (UINT)
is detected inside the macro program that is called using G code (or M
code).
