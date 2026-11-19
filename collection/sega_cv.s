#include <task_cst.h>

.section .text.keepboot

*-------------------------------------------------------
* vampirecollection-md: Castlevania-MD boot code with relay vectors.
*
* Both games share the one 68000 vector table at address 0. Vampire Killer is
* linked on its own at VK_BASE, with its own SGDK vector table there. The first
* long of RAM (GAME_FLAG) is an initialized variable of each build (see
* collection/cv.ld): 0 in Castlevania, VK_BASE in Vampire Killer. Each vector
* relays to Castlevania's handler, or to the same vector of Vampire Killer's
* table when GAME_FLAG is set.
*-------------------------------------------------------
#ifndef VK_BASE
#error VK_BASE must be defined
#endif
#define GAME_FLAG 0x00FF0000

*-------------------------------------------------------
*
*       Sega startup code for the GNU Assembler
*       Translated from:
*       Sega startup code for the Sozobon C compiler
*       Written by Paul W. Lee
*       Modified by Charles Coty
*       Modified by Stephane Dallongeville
*
*-------------------------------------------------------

    .globl  rom_header

    .org    0x00000000

_Start_Of_Rom:
_Vecteurs_68K:
        dc.l    __stack                 /* Stack address */
        dc.l    _Entry_Point            /* Program start address */
        dc.l    _tramp_2
        dc.l    _tramp_3
        dc.l    _tramp_4
        dc.l    _tramp_5
        dc.l    _tramp_6
        dc.l    _tramp_7
        dc.l    _tramp_8
        dc.l    _tramp_9
        dc.l    _tramp_10
        dc.l    _tramp_11
        dc.l    _tramp_12
        dc.l    _tramp_13
        dc.l    _tramp_14
        dc.l    _tramp_15
        dc.l    _tramp_16
        dc.l    _tramp_17
        dc.l    _tramp_18
        dc.l    _tramp_19
        dc.l    _tramp_20
        dc.l    _tramp_21
        dc.l    _tramp_22
        dc.l    _tramp_23
        dc.l    _tramp_24
        dc.l    _tramp_25
        dc.l    _tramp_26
        dc.l    _tramp_27
        dc.l    _tramp_28
        dc.l    _tramp_29
        dc.l    _tramp_30
        dc.l    _tramp_31
        dc.l    _tramp_32
        dc.l    _tramp_33
        dc.l    _tramp_34
        dc.l    _tramp_35
        dc.l    _tramp_36
        dc.l    _tramp_37
        dc.l    _tramp_38
        dc.l    _tramp_39
        dc.l    _tramp_40
        dc.l    _tramp_41
        dc.l    _tramp_42
        dc.l    _tramp_43
        dc.l    _tramp_44
        dc.l    _tramp_45
        dc.l    _tramp_46
        dc.l    _tramp_47
        dc.l    _tramp_48
        dc.l    _tramp_49
        dc.l    _tramp_50
        dc.l    _tramp_51
        dc.l    _tramp_52
        dc.l    _tramp_53
        dc.l    _tramp_54
        dc.l    _tramp_55
        dc.l    _tramp_56
        dc.l    _tramp_57
        dc.l    _tramp_58
        dc.l    _tramp_59
        dc.l    _tramp_60
        dc.l    _tramp_61
        dc.l    _tramp_62
        dc.l    _tramp_63

rom_header:
        .incbin "out/rom_header.bin", 0, 0x100

_Entry_Point:
* disable interrupts
        move    #0x2700,%sr

* Configure a USER_STACK_LENGTH bytes user stack at bottom, and system stack on top of it
        move    %sp, %usp
        sub     #USER_STACK_LENGTH, %sp

* Halt Z80 (need to be done as soon as possible on reset)
        move.l  #0xA11100,%a0       /* Z80_HALT_PORT */
        move.w  #0x0100,%d0
        move.w  %d0,(%a0)           /* HALT Z80 */
        move.w  %d0,0x0100(%a0)     /* END RESET Z80 */

* Reset while Vampire Killer ran: the RAM holds its state, never Castlevania's.
* Take the cold start path, which clears the RAM and so GAME_FLAG.
        tst.l   GAME_FLAG
        bne.s   ColdInit

        tst.l   0xa10008
        bne.s   SkipInit

        tst.w   0xa1000c
        bne.s   SkipInit

ColdInit:
* Check Version Number
        move.b  -0x10ff(%a0),%d0
        andi.b  #0x0f,%d0
        beq.s   NoTMSS

* Sega Security Code (SEGA)
        move.l  #0x53454741,0x2f00(%a0)

NoTMSS:
        jmp     _start_entry

SkipInit:
        jmp     _reset_entry



*------------------------------------------------
*       relay vectors
*------------------------------------------------

.macro TRAMP idx, target
_tramp_\idx:
        tst.l   GAME_FLAG
        bne.s   1f
        jmp     \target
1:      move.l  (VK_BASE + \idx * 4), -(%sp)
        rts
.endm

        TRAMP   2, _Bus_Error
        TRAMP   3, _Address_Error
        TRAMP   4, _Illegal_Instruction
        TRAMP   5, _Zero_Divide
        TRAMP   6, _Chk_Instruction
        TRAMP   7, _Trapv_Instruction
        TRAMP   8, _Privilege_Violation
        TRAMP   9, _Trace
        TRAMP   10, _Line_1010_Emulation
        TRAMP   11, _Line_1111_Emulation
        TRAMP   12, _Error_Exception
        TRAMP   13, _Error_Exception
        TRAMP   14, _Error_Exception
        TRAMP   15, _Error_Exception
        TRAMP   16, _Error_Exception
        TRAMP   17, _Error_Exception
        TRAMP   18, _Error_Exception
        TRAMP   19, _Error_Exception
        TRAMP   20, _Error_Exception
        TRAMP   21, _Error_Exception
        TRAMP   22, _Error_Exception
        TRAMP   23, _Error_Exception
        TRAMP   24, _Error_Exception
        TRAMP   25, _INT
        TRAMP   26, _EXTINT
        TRAMP   27, _INT
        TRAMP   28, hintCaller
        TRAMP   29, _INT
        TRAMP   30, _VINT
        TRAMP   31, _INT
        TRAMP   32, _trap_0
        TRAMP   33, _INT
        TRAMP   34, _INT
        TRAMP   35, _INT
        TRAMP   36, _INT
        TRAMP   37, _INT
        TRAMP   38, _INT
        TRAMP   39, _INT
        TRAMP   40, _INT
        TRAMP   41, _INT
        TRAMP   42, _INT
        TRAMP   43, _INT
        TRAMP   44, _INT
        TRAMP   45, _INT
        TRAMP   46, _INT
        TRAMP   47, _INT
        TRAMP   48, _INT
        TRAMP   49, _INT
        TRAMP   50, _INT
        TRAMP   51, _INT
        TRAMP   52, _INT
        TRAMP   53, _INT
        TRAMP   54, _INT
        TRAMP   55, _INT
        TRAMP   56, _INT
        TRAMP   57, _INT
        TRAMP   58, _INT
        TRAMP   59, _INT
        TRAMP   60, _INT
        TRAMP   61, _INT
        TRAMP   62, _INT
        TRAMP   63, _INT

*------------------------------------------------
*
*       interrupt functions
*
*------------------------------------------------

_INT:
        movem.l %d0-%d1/%a0-%a1,-(%sp)
        move.l  intCB, %a0
        jsr    (%a0)
        movem.l (%sp)+,%d0-%d1/%a0-%a1
        rte

_EXTINT:
        movem.l %d0-%d1/%a0-%a1,-(%sp)
        move.l  eintCB, %a0
        jsr    (%a0)
        movem.l (%sp)+,%d0-%d1/%a0-%a1
        rte

_VINT:
        btst    #5, (%sp)       /* Skip context switch if not in user task */
        bne.s   no_user_task

        tst.w   task_lock
        bne.s   1f
        move.w  #0, -(%sp)      /* TSK_superPend() will return 0 */
        bra.s   unlock          /* If lock == 0, supervisor task is not locked */

1:
        bcs.s   no_user_task    /* If lock < 0, super is locked with infinite wait */
        subq.w  #1, task_lock   /* Locked with wait, subtract 1 to the frame count */
        bne.s   no_user_task    /* And do not unlock if we did not reach 0 */
        move.w  #1, -(%sp)      /* TSK_superPend() will return 1 */

unlock:
        /* Save bg task registers (excepting a7, that is stored in usp) */
        move.l  %a0, task_regs
        lea     (task_regs + UTSK_REGS_LEN), %a0
        movem.l %d0-%d7/%a1-%a6, -(%a0)

        move.w  (%sp)+, %d0     /* Load return value previously pushed to stack */

        move.w  (%sp)+, task_sr /* Pop user task sr and pc, and save them, */
        move.l  (%sp)+, task_pc /* so they can be restored later.          */
        movem.l (%sp)+, %d2-%d7/%a2-%a6 /* Restore non clobberable registers */

no_user_task:
        /* At this point, we always have in the stack the SR and PC of the task */
        /* we want to jump after processing the interrupt, that might be the    */
        /* point where we came from (if there is no context switch) or the      */
        /* supervisor task (if we unlocked it).                                 */

        movem.l %d0-%d1/%a0-%a1,-(%sp)
        ori.w   #0x0001, intTrace           /* in V-Int */
        addq.l  #1, vtimer                  /* increment frame counter (more a vint counter) */

        move.l  z80VIntCB, %a0              /* load Z80 V-Int handler */
        jsr     (%a0)                       /* call user callback */

        btst    #1, VBlankProcess+1         /* PROCESS_BITMAP_TASK ? (use VBlankProcess+1 as btst is a byte operation) */
        beq.s   no_bmp_task

        jsr     BMP_doVBlankProcess         /* do BMP vblank task */

no_bmp_task:
        move.l  vintCB, %a0                 /* load user callback */
        jsr     (%a0)                       /* call user callback */
        andi.w  #0xFFFE, intTrace           /* out V-Int */
        movem.l (%sp)+,%d0-%d1/%a0-%a1
        rte

*------------------------------------------------
*
* Copyright (c) 1988 by Sozobon, Limited.  Author: Johann Ruegg
*
* Permission is granted to anyone to use this software for any purpose
* on any computer system, and to redistribute it freely, with the
* following restrictions:
* 1) No charge may be made other than reasonable charges for reproduction.
* 2) Modified versions must be clearly marked as such.
* 3) The authors are not responsible for any harmful consequences
*    of using this software, even if they result from defects in it.
*
*------------------------------------------------

ldiv:
        move.l  4(%a7),%d0
        bpl     ld1
        neg.l   %d0
ld1:
        move.l  8(%a7),%d1
        bpl     ld2
        neg.l   %d1
        eor.b   #0x80,4(%a7)
ld2:
        bsr     i_ldiv          /* d0 = d0/d1 */
        tst.b   4(%a7)
        bpl     ld3
        neg.l   %d0
ld3:
        rts

lmul:
        move.l  4(%a7),%d0
        bpl     lm1
        neg.l   %d0
lm1:
        move.l  8(%a7),%d1
        bpl     lm2
        neg.l   %d1
        eor.b   #0x80,4(%a7)
lm2:
        bsr     i_lmul          /* d0 = d0*d1 */
        tst.b   4(%a7)
        bpl     lm3
        neg.l   %d0
lm3:
        rts

lrem:
        move.l  4(%a7),%d0
        bpl     lr1
        neg.l   %d0
lr1:
        move.l  8(%a7),%d1
        bpl     lr2
        neg.l   %d1
lr2:
        bsr     i_ldiv          /* d1 = d0%d1 */
        move.l  %d1,%d0
        tst.b   4(%a7)
        bpl     lr3
        neg.l   %d0
lr3:
        rts

ldivu:
        move.l  4(%a7),%d0
        move.l  8(%a7),%d1
        bsr     i_ldiv
        rts

lmulu:
        move.l  4(%a7),%d0
        move.l  8(%a7),%d1
        bsr     i_lmul
        rts

lremu:
        move.l  4(%a7),%d0
        move.l  8(%a7),%d1
        bsr     i_ldiv
        move.l  %d1,%d0
        rts
*
* A in d0, B in d1, return A*B in d0
*
i_lmul:
        move.l  %d3,%a2           /* save d3 */
        move.w  %d1,%d2
        mulu    %d0,%d2           /* d2 = Al * Bl */

        move.l  %d1,%d3
        swap    %d3
        mulu    %d0,%d3           /* d3 = Al * Bh */

        swap    %d0
        mulu    %d1,%d0           /* d0 = Ah * Bl */

        add.l   %d3,%d0           /* d0 = (Ah*Bl + Al*Bh) */
        swap    %d0
        clr.w   %d0               /* d0 = (Ah*Bl + Al*Bh) << 16 */

        add.l   %d2,%d0           /* d0 = A*B */
        move.l  %a2,%d3           /* restore d3 */
        rts
*
*A in d0, B in d1, return A/B in d0, A%B in d1
*
i_ldiv:
        tst.l   %d1
        bne     nz1

*       divide by zero
*       divu    #0,%d0            /* cause trap */
        move.l  #0x80000000,%d0
        move.l  %d0,%d1
        rts
nz1:
        move.l  %d3,%a2           /* save d3 */
        cmp.l   %d1,%d0
        bhi     norm
        beq     is1
*       A<B, so ret 0, rem A
        move.l  %d0,%d1
        clr.l   %d0
        move.l  %a2,%d3           /* restore d3 */
        rts
*       A==B, so ret 1, rem 0
is1:
        moveq.l #1,%d0
        clr.l   %d1
        move.l  %a2,%d3           /* restore d3 */
        rts
*       A>B and B is not 0
norm:
        cmp.l   #1,%d1
        bne     not1
*       B==1, so ret A, rem 0
        clr.l   %d1
        move.l  %a2,%d3           /* restore d3 */
        rts
*  check for A short (implies B short also)
not1:
        cmp.l   #0xffff,%d0
        bhi     slow
*  A short and B short -- use 'divu'
        divu    %d1,%d0           /* d0 = REM:ANS */
        swap    %d0               /* d0 = ANS:REM */
        clr.l   %d1
        move.w  %d0,%d1           /* d1 = REM */
        clr.w   %d0
        swap    %d0
        move.l  %a2,%d3           /* restore d3 */
        rts
* check for B short
slow:
        cmp.l   #0xffff,%d1
        bhi     slower
* A long and B short -- use special stuff from gnu
        move.l  %d0,%d2
        clr.w   %d2
        swap    %d2
        divu    %d1,%d2           /* d2 = REM:ANS of Ahi/B */
        clr.l   %d3
        move.w  %d2,%d3           /* d3 = Ahi/B */
        swap    %d3

        move.w  %d0,%d2           /* d2 = REM << 16 + Alo */
        divu    %d1,%d2           /* d2 = REM:ANS of stuff/B */

        move.l  %d2,%d1
        clr.w   %d1
        swap    %d1               /* d1 = REM */

        clr.l   %d0
        move.w  %d2,%d0
        add.l   %d3,%d0           /* d0 = ANS */
        move.l  %a2,%d3           /* restore d3 */
        rts
*       A>B, B > 1
slower:
        move.l  #1,%d2
        clr.l   %d3
moreadj:
        cmp.l   %d0,%d1
        bhs     adj
        add.l   %d2,%d2
        add.l   %d1,%d1
        bpl     moreadj
* we shifted B until its >A or sign bit set
* we shifted #1 (d2) along with it
adj:
        cmp.l   %d0,%d1
        bhi     ltuns
        or.l    %d2,%d3
        sub.l   %d1,%d0
ltuns:
        lsr.l   #1,%d1
        lsr.l   #1,%d2
        bne     adj
* d3=answer, d0=rem
        move.l  %d0,%d1
        move.l  %d3,%d0
        move.l  %a2,%d3           /* restore d3 */
        rts
