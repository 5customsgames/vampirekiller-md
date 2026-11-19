#include <genesis.h>

__attribute__((externally_visible))
// Full-width header fields are binary data, without a C string terminator.
const ROMHeader rom_header = {
#if (MODULE_MEGAWIFI && (MEGAWIFI_IMPLEMENTATION == MEGAWIFI_IMPLEMENTATION_MW_CART))
    { 'S', 'E', 'G', 'A', ' ', 'M', 'E', 'G', 'A', 'W', 'I', 'F', 'I', ' ', ' ', ' ' },
#elif (ENABLE_BANK_SWITCH != 0)
    { 'S', 'E', 'G', 'A', ' ', 'S', 'S', 'F', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
#else
    { 'S', 'E', 'G', 'A', ' ', 'M', 'E', 'G', 'A', ' ', 'D', 'R', 'I', 'V', 'E', ' ' },
#endif
    { '(', 'C', ')', '5', 'C', 'u', 's', 't', 'o', 'm', 's', ' ', '2', '0', '2', '6' },
    { 'V', 'a', 'm', 'p', 'i', 'r', 'e', ' ', 'C', 'o', 'l', 'l', 'e', 'c', 't', 'i', 'o', 'n', '-', 'M', 'D', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
    { 'V', 'a', 'm', 'p', 'i', 'r', 'e', ' ', 'C', 'o', 'l', 'l', 'e', 'c', 't', 'i', 'o', 'n', '-', 'M', 'D', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
    { 'G', 'M', ' ', '5', 'C', 'V', 'C', 'O', 'L', '-', '0', '1', ' ', ' ' },
    0x000,
    { 'J', 'D', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
    0x00000000,
#if (ENABLE_BANK_SWITCH != 0)
    0x003FFFFF,
#else
    0x000FFFFF,
#endif
    0xE0FF0000,
    0xE0FFFFFF,
    // no SRAM: neither game saves, and 0x200000 is ROM here
    { ' ', ' ' },
    0x2020,
    0x20202020,
    0x20202020,
    { ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
    "PORT BY 5CUSTOMS STUDIO",
    { 'J', 'U', 'E', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' }
};
