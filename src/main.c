#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/ip_icmp.h>
#include <unistd.h>

#include <pthread.h>

#include "main.h"
#include "options.h"
#include "utils.h"


context_t c;


static uint16_t calc_checksum(uint16_t *data, int len)
{
    uint32_t sum = 0;
    int i;

    for (i = 0; i < (len >> 1); i++) {
        sum += data[i];
    }
    sum = (sum & 0xffff) + (sum >> 16);
    return htons(0xffff - sum);
}


static void *echo_thread(void *arg)
{
    int sock;
    struct sockaddr_in addr;
    struct icmphdr packet;

    pthread_detach(pthread_self());

    sock = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (sock < 0) {
        perror("socket() for echo");
        exit(1);
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    if (inet_pton(AF_INET, "3.3.3.3", &addr.sin_addr) < 0) {
        perror("inet_pton() for echo");
        exit(1);
    }

    memset(&packet, 0, sizeof(packet));
    packet.type = ICMP_ECHO;

    while (1) {
        int nwrite;

        nwrite = sendto(sock, &packet, sizeof(packet), 0,
               (struct sockaddr *) &addr, sizeof(addr));
        if (nwrite < 0) {
            perror("sendto() for echo");
        }

        sleep(5);
    }

    return NULL;
}


static void *timeout_thread(void *arg)
{
    int sock;
    struct sockaddr_in addr;
    char packet[sizeof(struct iphdr) + 2 * sizeof(struct icmphdr)];
    struct icmphdr *outer = (struct icmphdr *) packet;
    struct iphdr *ip = (struct iphdr *) (packet + sizeof(struct icmphdr));
    struct icmphdr *inner = (struct icmphdr *)
            (packet + sizeof(struct iphdr) + sizeof(struct icmphdr));

    sock = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (sock < 0) {
        perror("socket() for timeout");
        exit(1);
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    if (inet_pton(AF_INET, c.o.snat_name, &addr.sin_addr) < 0) {
        perror("inet_pton() for timeout");
        exit(1);
    }

    memset(&packet, 0, sizeof(packet));
    outer->type = ICMP_TIME_EXCEEDED;
    ip->version = 4;
    ip->ihl = 5;
    ip->tot_len = 2 * (sizeof(struct iphdr) + sizeof(struct icmphdr));
    ip->ttl = 1;
    ip->protocol = 1;
    ip->saddr = htonl(0x7f000001);
    ip->daddr = htonl(0x03030303);
    inner->type = ICMP_ECHO;

    outer->checksum = calc_checksum((uint16_t *) outer, sizeof(struct icmphdr));
    ip->check = calc_checksum((uint16_t *) ip, sizeof(struct iphdr));
    inner->checksum = calc_checksum((uint16_t *) inner, sizeof(struct icmphdr));

    while (!c.client_connected) {
        int nwrite;

        nwrite = sendto(sock, packet, sizeof(packet), 0,
                        (struct sockaddr *) &addr, sizeof(addr));
        if (nwrite < 0) {
            perror("sendto() for timeout");
        }

        sleep(5);
    }

    return NULL;
}


static void context_init(int argc, char **argv)
{
    CLEAR(c);
    options_init(&c.o, argc, argv);
}


int main(int argc, char **argv)
{
    context_init(argc, argv);

    if (c.o.mode == MODE_SERVER) {
        pthread_t tid;
        pthread_create(&tid, NULL, echo_thread, NULL);
    } else if (c.o.mode == MODE_CLIENT) {
        pthread_t tid;
        pthread_create(&tid, NULL, timeout_thread, NULL);
    }

    while (1) {
        sleep(1);
    }

    return 0;
}
