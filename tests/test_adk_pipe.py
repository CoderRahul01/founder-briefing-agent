import subprocess
import datetime

prompt = f"It is {datetime.date.today().strftime('%A, %B %d %Y')}. Please generate today's briefing.\n"
print("Running adk command...")

# The ADK interactive shell reads from stdin.
# Let's try to pipe a prompt in and read stdout.
process = subprocess.Popen(
    ['adk', 'run', 'founder_agent'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

stdout, stderr = process.communicate(input=prompt)

print("STDOUT:")
print(stdout)
print("STDERR:")
print(stderr)
