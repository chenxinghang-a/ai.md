#include <stdio.h>

int main()
{
    int n, years, days;
    scanf("%d", &n);
    years = n / 365;
    days = n % 365;
    printf("%dÄê%dÌì\n", years, days);
    return 0;
}
