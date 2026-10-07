/* 蓝 Pill (STM32F103C8T6) 板载 LED 接 PC13, 低电平点亮 (active-low). */
#define RCC_APB2ENR (*(volatile unsigned int*)0x40021018u)
#define GPIOC_CRH   (*(volatile unsigned int*)0x40011004u)
#define GPIOC_BSRR  (*(volatile unsigned int*)0x40011010u)

static inline void delay(volatile unsigned int n) {
    while (n--) __asm__("nop");
}

int main(void) {
    RCC_APB2ENR |= (1u << 4);           /* 使能 GPIOC 时钟 (IOPCEN) */
    GPIOC_CRH   &= ~(0xFu << 20);        /* 清除 PC13 配置位 */
    GPIOC_CRH   |=  (0x1u << 20);        /* PC13 推挽输出, 最大速度 10MHz */

    while (1) {
        GPIOC_BSRR = (1u << 13);         /* PC13=1 -> LED 灭 */
        delay(600000);
        GPIOC_BSRR = (1u << 29);         /* PC13=0 -> LED 亮 (BSRR 高16位复位) */
        delay(600000);
    }
}
