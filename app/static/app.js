// Keyboard shortcuts for the question view (specs/TRAINER.md §6.2):
// a-d pick an option, arrows navigate, f flags, enter checks/advances.
document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "TEXTAREA" || (e.target.tagName === "INPUT" && e.target.type === "text")) return;

  const letters = { a: 0, b: 1, c: 2, d: 3 };
  if (e.key.toLowerCase() in letters) {
    const radios = document.querySelectorAll('input[type=radio][name=answer]');
    const radio = radios[letters[e.key.toLowerCase()]];
    // A course option already tried is disabled, and a solved question's whole
    // fieldset is: `:disabled` sees both, the `disabled` property only the first.
    if (radio && !radio.matches(":disabled")) radio.checked = true;
    return;
  }
  if (e.key === "ArrowLeft") {
    const link = document.getElementById("prev-link");
    if (link) link.click();
  } else if (e.key === "ArrowRight") {
    const link = document.getElementById("next-link");
    if (link) link.click();
  } else if (e.key.toLowerCase() === "f") {
    const flag = document.querySelector('input[name=flag]');
    if (flag) flag.checked = !flag.checked;
  } else if (e.key === "Enter") {
    const form = document.querySelector('form[action*="/answer"]');
    if (form) form.requestSubmit();
  }
});

// The section/count choice only applies to study mode -- sample_exam always
// draws from the full question pool, so hide it once "exam" is selected.
const modeRadios = document.querySelectorAll('#new-session input[name=mode]');
const studyOnly = document.getElementById("study-only");
if (modeRadios.length && studyOnly) {
  const syncStudyOnly = () => {
    const checked = document.querySelector('#new-session input[name=mode]:checked');
    studyOnly.hidden = !!checked && checked.value !== "study";
  };
  modeRadios.forEach((r) => r.addEventListener("change", syncStudyOnly));
  syncStudyOnly();
}

// An open course answer waits for the grader, a few seconds (specs/LEARN-2-3.md
// §4.4): the button says so, and a second click cannot post it twice.
document.querySelectorAll("form.open-answer").forEach((form) => {
  form.addEventListener("submit", () => {
    const button = form.querySelector("button[data-grading]");
    if (button) {
      button.textContent = button.dataset.grading;
      button.disabled = true;
    }
  });
});
