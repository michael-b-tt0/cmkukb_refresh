/* Checked against the installed MSKLC 1.4 inc/kbd.h, not a replacement struct. */
#if !defined(NTDDI_VERSION) || !defined(NTDDI_WINXP)
#error NTDDI version constants must be defined before kbd.h
#elif NTDDI_VERSION < NTDDI_WINXP
#error This layout requires the full XP-or-later KBDTABLES
#endif

#define ABI_ASSERT(name, test) typedef char abi_##name[(test) ? 1 : -1]
#define ABI_OFFSET(field, value) ABI_ASSERT(field, FIELD_OFFSET(KBDTABLES, field) == value)

#if defined(_WIN64) || defined(BUILD_WOW6432)
ABI_ASSERT(size, sizeof(KBDTABLES) == 104);
ABI_OFFSET(pCharModifiers, 0);
ABI_OFFSET(pVkToWcharTable, 8);
ABI_OFFSET(pDeadKey, 16);
ABI_OFFSET(pKeyNames, 24);
ABI_OFFSET(pKeyNamesExt, 32);
ABI_OFFSET(pKeyNamesDead, 40);
ABI_OFFSET(pusVSCtoVK, 48);
ABI_OFFSET(bMaxVSCtoVK, 56);
ABI_OFFSET(pVSCtoVK_E0, 64);
ABI_OFFSET(pVSCtoVK_E1, 72);
ABI_OFFSET(fLocaleFlags, 80);
ABI_OFFSET(nLgMax, 84);
ABI_OFFSET(cbLgEntry, 85);
ABI_OFFSET(pLigature, 88);
ABI_OFFSET(dwType, 96);
ABI_OFFSET(dwSubType, 100);
#else
ABI_ASSERT(size, sizeof(KBDTABLES) == 60);
ABI_OFFSET(pCharModifiers, 0);
ABI_OFFSET(pVkToWcharTable, 4);
ABI_OFFSET(pDeadKey, 8);
ABI_OFFSET(pKeyNames, 12);
ABI_OFFSET(pKeyNamesExt, 16);
ABI_OFFSET(pKeyNamesDead, 20);
ABI_OFFSET(pusVSCtoVK, 24);
ABI_OFFSET(bMaxVSCtoVK, 28);
ABI_OFFSET(pVSCtoVK_E0, 32);
ABI_OFFSET(pVSCtoVK_E1, 36);
ABI_OFFSET(fLocaleFlags, 40);
ABI_OFFSET(nLgMax, 44);
ABI_OFFSET(cbLgEntry, 45);
ABI_OFFSET(pLigature, 48);
ABI_OFFSET(dwType, 52);
ABI_OFFSET(dwSubType, 56);
#endif

ABI_ASSERT(caps_is_backspace, T3A == VK_BACK);
ABI_ASSERT(backspace_unchanged, T0E == VK_BACK);
