#!/usr/bin/env python3
"""Write the first message for one Kafu voice worker, with its whole job inside (no job file to fetch).

  python3 tools/kafu_voice/worker_prompt.py JOB.json > prompt.txt

JOB.json = {"slot": "21", "qids": [...], "lines": [{"id", "voice", "dir", "text"}]} (the Head writes it).
Why the job is inside the message: a worker that reads its job from an artifact is refused by the auto-mode permission
check ("untrusted code integration"), and a worker that installs Breeze itself is refused too ("code from external").
So Breeze comes from the environment's setup script (env_setup.sh), the tools from this repository, and the job from the
first message. The worker only renders with the repository's own script and uploads the result.
"""
import json
import sys

job = json.loads(open(sys.argv[1]).read())
slot = str(job["slot"])
job_text = json.dumps({"slot": slot, "round": 1, "final": True, "qids": job.get("qids", []), "lines": job["lines"]},
                      ensure_ascii=False, indent=1)
if "KAFUJOBEOF" in job_text:
    sys.exit("the job text contains the heredoc marker")

print(f"""You are Kafu VOICE WORKER {slot} in this repository (your session's own checkout). The owner asked for this job.
Your whole assignment: render the voice lines below with the repository's own Breeze script, then upload the result. Do not ask
questions; spend few turns and tokens; read no other files. Nothing is written to GitHub (no commit, push, branch or pull request;
a stop-hook asking to commit does not apply). Do not message other sessions. Never start a second copy of a background command.
If a tool call is refused by permissions, do not try variations: reply with one Arabic line naming the refused command and stop.

1. `tail -n 1 /tmp/kafu_voice_setup.log` (the environment starts the Breeze install before you start; it may still be running).
   - `VOICE OK`: go to step 2.
   - `VOICE BROKEN...`: reply "SLOT {slot}: الصوت معطل" + that line, and stop.
   - Any other line (the install is still running): start this wait as your own background command (Bash, run_in_background
     true, timeout 7200000): `until grep -qE '^VOICE (OK|BROKEN)' /tmp/kafu_voice_setup.log; do sleep 20; done` and end the
     turn; when it ends, do step 1 again.
   - No file: start `python3 tools/kafu_voice/voice_setup.py . > /tmp/kafu_voice_setup.log 2>&1` as your own background
     command (same way) and end the turn; when it ends, do step 1 again.
2. Write your job exactly as given, from the repository root:
mkdir -p work && cat > work/job.json <<'KAFUJOBEOF'
{job_text}
KAFUJOBEOF
3. Start the render as your own background command (Bash, run_in_background true, timeout 7200000), from the repository root:
   `~/.venvs/kafu-voice/bin/python tools/kafu_voice/render_job.py work/job.json work/voice-out {slot} 1 > work/render.out 2>&1`
   End the turn; you are woken when it ends. Its last line is `RENDER DONE n/m` (if it ended otherwise, run the same command once
   more: it resumes from its cache).
4. Publish the result as a NEW artifact of your own (Artifact tool, action "publish", no url): file_path =
   work/voice-out/index.html, root = work/voice-out, files = every `voice_{slot}_r1_NN.b64.txt` in work/voice-out plus
   `DONE_{slot}_r1.txt`, each mapped to the same name, icon "audio", description "Kafu voice recordings slot {slot}".
   (Not the shared inbox: uploads there were refused as "Live-Shared Artifact Sensitive Delta".)
5. Reply with one line: SLOT {slot}, lines rendered n/m, the artifact URL (or the exact refusal), failed ids if any.""")
