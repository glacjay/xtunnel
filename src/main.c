#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/ip_icmp.h>


int main(void)
{
    int dummy_sock;
    struct icmphdr icmp_dummy;
    struct sockaddr_in dummy_addr;

    dummy_sock = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (dummy_sock < 0) {
        perror("socket() for dummy_sock");
        exit(1);
    }

    memset(&icmp_dummy, 0, sizeof(icmp_dummy));
    icmp_dummy.type = ICMP_ECHO;
    icmp_dummy.code = 0; // Must be 0

    memset(&dummy_addr, 0, sizeof(dummy_addr));
    dummy_addr.sin_family = AF_INET;
    if (inet_pton(AF_INET, "192.168.7.2", &dummy_addr.sin_addr) < 0) {
        perror("inet_pton() for dummy_addr");
        exit(1);
    }

    while (1) {
        int nwrite;

        nwrite = sendto(dummy_sock, &icmp_dummy, sizeof(icmp_dummy), 0,
               (struct sockaddr *) &dummy_addr, sizeof(dummy_addr));
        if (nwrite < 0) {
            perror("sendto() for dummy_sock");
            exit(1);
        }

        sleep(5);
    }

    return 0;
}
