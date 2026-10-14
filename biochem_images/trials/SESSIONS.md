# Overnight experiment: cavernous sinus mnemonic, 10 settings

Leader session: session_01EgkwjvrVaqjpuUfdYHYHQ2. The `claude/cs-trial-NN` branches were NOT created: workers
are on `claude/ai-biochemistry-image-generation-efl9y3` and push their results there, each only into its own folder
`biochem_images/trials/out/NN/` (image.png, report.md, result.json). Check with `git pull --rebase` and `ls biochem_images/trials/out`.
Opened 2026-10-13 23:35 UTC.

| # | Session | Settings | Est. total |
|---|---|---|---|
| 01 | session_0138Xn38ji9vz29mPvhRu8xV | turbo Q6 768 (baseline) | 1.1 h |
| 02 | session_01ThPUauXnqGjwa4WcXxJYdy | turbo Q4_K 768 | 1.1 h |
| 03 | session_01AJhKdzpqA1m1PNmCShMXsN | turbo Q5_0 768, no offload flag | 1.3 h |
| 04 | session_01AVyZTqMi4XNwHBvsJH6Xtu | turbo Q6 1024 | 2.6 h |
| 05 | session_01Vjycn89GT6KbAWE9FsNTv4 | turbo Q6 1280x720 | 2.0 h |
| 06 | session_01NGMwCVEhUAkwRSRXkK4ouN | turbo Q6 768, prompt without text | 1.1 h |
| 07 | session_01PDkFxEusFYWHNF5Rva5gRz | turbo Q6 768, text-rich prompt | 1.1 h |
| 08 | session_01THWh2CSwn8SiNqX3ettXNk | full Q4_K CFG4 12 steps 768 | 3.1 h |
| 09 | session_012GjqHzkzpa5xhb13f1QND3 | full Q6 CFG4 20 steps 768 | 4.5 h |
| 10 | session_01BGwp1VvdLGPiu3m8rgjHoR | full Q6 CFG4 12 steps 1024 | 5.5 h |

## Leader plan (keep checks cheap)

1. Check with `git pull --rebase -q; ls biochem_images/trials/out` (which workers pushed) and one
   `list_sessions` call. Read a worker's events only if its status is failed or it is overdue.
2. Check-ins: +30 min (all started?), +90 min, +3 h, +4.5 h, +6 h. Then stop waiting.
3. A worker overdue by more than 1.5 h, or failed/idle without a push: read its last events,
   send_message with the fix, or rerun the trial in a new session.
4. When done: results are already in this branch under out/NN; build a contact sheet with settings under each image, push, send the 10 images to the user.
