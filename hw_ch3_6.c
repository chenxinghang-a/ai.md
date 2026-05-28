#include <stdio.h>

int main()
{
    char c1, c2;
    c1 = getchar();
    c2 = getchar();
    printf("用putchar输出语句 ");
    putchar(c1);
    putchar(c2);
    printf("\n");
    printf("用printf输出语句 %c%c\n", c1, c2);
    return 0;
}
