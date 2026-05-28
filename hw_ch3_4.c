#include <stdio.h>

int main()
{
    int a, b;
    double x, y;
    char c1, c2;

    scanf("%d%d%lf%lf %c%c", &a, &b, &x, &y, &c1, &c2);
    printf("a=%d,b=%d,x=%.2f,y=%.2f,c1=%c,c2=%c\n", a, b, x, y, c1, c2);

    return 0;
}
