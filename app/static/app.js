// Keyboard shortcuts for the question view (specs/APP.md §6.2):
// a-d pick an option, arrows navigate, f flags, enter checks/advances.
document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "TEXTAREA" || (e.target.tagName === "INPUT" && e.target.type === "text")) return;

  const letters = { a: 0, b: 1, c: 2, d: 3 };
  if (e.key.toLowerCase() in letters) {
    const radios = document.querySelectorAll('input[type=radio][name=answer]');
    const radio = radios[letters[e.key.toLowerCase()]];
    if (radio) radio.checked = true;
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
