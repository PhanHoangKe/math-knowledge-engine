MKE AUTOMATED REMEDIATION

Task: THPT-COV-P1-R1-002
Audit event: c4ea42b6992d8a22d6309de9a8ebf7f9c58fa8bd35b5331542ed598916ee3ff9

- [HIGH] deterministic-gates: independent full regression failed Required: Correct the failure without broadening the original allowed scope.

Preserve the original task contract and allowed paths. CAS outputs remain untrusted candidates; only MKE verification grants trust. Do not modify frontend, protected/default branches, or files outside allowed_prefixes. Do not perform git operations.
