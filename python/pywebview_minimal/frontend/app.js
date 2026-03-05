const output = document.getElementById("output");
const btnPing = document.getElementById("btn-ping");
const btnEcho = document.getElementById("btn-echo");
const btnJob = document.getElementById("btn-job");
const echoInput = document.getElementById("echo-input");
const jobSeconds = document.getElementById("job-seconds");

function write(data) {
  output.textContent = `${new Date().toLocaleTimeString()}\n${JSON.stringify(data, null, 2)}`;
}

function setBusy(button, busy) {
  button.disabled = busy;
  button.textContent = busy ? "Running..." : button.dataset.label;
}

btnPing.dataset.label = "Ping";
btnEcho.dataset.label = "Echo";
btnJob.dataset.label = "Run";

btnPing.addEventListener("click", async () => {
  try {
    const res = await window.pywebview.api.ping();
    write(res);
  } catch (err) {
    write({ error: String(err) });
  }
});

btnEcho.addEventListener("click", async () => {
  try {
    const text = echoInput.value || "";
    const res = await window.pywebview.api.echo(text);
    write(res);
  } catch (err) {
    write({ error: String(err) });
  }
});

btnJob.addEventListener("click", async () => {
  setBusy(btnJob, true);
  try {
    const seconds = Number(jobSeconds.value || 2);
    const res = await window.pywebview.api.fake_job(seconds);
    write(res);
  } catch (err) {
    write({ error: String(err) });
  } finally {
    setBusy(btnJob, false);
  }
});
