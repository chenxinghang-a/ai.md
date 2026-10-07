.syntax unified
.cpu cortex-m3
.thumb

.section .isr_vector, "a"
.align 2
.word 0x20005000          /* Top of Stack (20KB SRAM end for F103C8) */
.word Reset_Handler       /* Reset vector */
.fill 62, 4, 0            /* remaining vectors left at 0 (no interrupts used) */

.section .text.Reset_Handler
.thumb_func
.global Reset_Handler
Reset_Handler:
    bl main
1:  b 1b
