# S4-B2/P0-R1 Native vs ctypes Matrix

| Property | Native C++ | Broken P0 ctypes | Corrected ctypes |
|---|---:|---:|---:|
| Pointer/HANDLE size | 8 | 8 | 8 |
| `STARTUPINFOW` size | 104 | **96** | 104 |
| `STARTUPINFOEXW` size | 112 | **104** | 112 |
| `lpAttributeList` offset | 104 | **96** | 104 |
| `SECURITY_CAPABILITIES` size/alignment | 24 / 8 | 24 / 8 | 24 / 8 |
| One/two attribute bytes | 48 / 72 | 48 / 72 | 48 / 72 |
| A normal launch | PASS | PASS | PASS |
| B AppContainer-only | PASS | **FAIL 87** | PASS |
| C handle-list-only | PASS | **FAIL 87** | PASS |
| D combined | PASS | **FAIL 87** | PASS |
| B/D token AppContainer and SID match | true | not created | true |
| C/D allowlisted handle inherited | true | not created | true |
| C/D inheritable decoy excluded | true | not created | true |
| Child elevated | false | not created | false |
| Profile deletion HRESULT | 0 | 0 | 0 |

Root-cause delta: broken `STARTUPINFOW._fields_` omitted `dwYCountChars`,
shifting all later fields and the `STARTUPINFOEXW.lpAttributeList` tail.
