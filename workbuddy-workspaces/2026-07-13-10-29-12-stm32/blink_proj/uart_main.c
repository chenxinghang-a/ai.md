/* 蓝 Pill USART1 (PA9=TX, PA10=RX) 回显, 115200-8-N-1.
   USB-TTL 接法: TTL-TX->PA10, TTL-RX->PA9, GND->GND */
#define RCC_APB2ENR (*(volatile unsigned int*)0x40021018u)
#define GPIOA_CRH   (*(volatile unsigned int*)0x40010804u)
#define USART1_BASE 0x40013800u
#define USART1_SR   (*(volatile unsigned int*)(USART1_BASE + 0x00))
#define USART1_DR   (*(volatile unsigned int*)(USART1_BASE + 0x04))
#define USART1_BRR  (*(volatile unsigned int*)(USART1_BASE + 0x08))
#define USART1_CR1  (*(volatile unsigned int*)(USART1_BASE + 0x0C))

static inline void delay(volatile unsigned int n){ while(n--) __asm__("nop"); }

static int uart_getc(void){
    while(!(USART1_SR & (1u<<5)));          /* 等待 RXNE */
    return (int)(USART1_DR & 0xFF);
}
static void uart_putc(int c){
    while(!(USART1_SR & (1u<<7)));          /* 等待 TXE */
    USART1_DR = (unsigned)c & 0xFF;
}

int main(void){
    RCC_APB2ENR |= (1u<<2);                 /* IOPAEN */
    RCC_APB2ENR |= (1u<<14);                /* USART1EN */
    GPIOA_CRH &= ~(0xFFu<<4);
    GPIOA_CRH |= (0xBu<<4) | (0x4u<<8);     /* PA9 复用推挽, PA10 浮空输入 */
    USART1_BRR = 625;                       /* 72MHz / 115200 = 625 */
    USART1_CR1 = (1u<<13)|(1u<<3)|(1u<<2);  /* UE, TE, RE */

    const char *msg = "READY\r\n";
    for(const char *p=msg; *p; p++) uart_putc(*p);

    while(1){
        int c = uart_getc();                /* 收到啥回显啥 */
        uart_putc(c);
    }
}
