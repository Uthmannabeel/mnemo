// Shared theme toggle. The pre-paint theme script lives inline in each page's <head>.
(function () {
  var btn = document.getElementById('themeToggle');
  if (!btn) return;
  function sync() {
    btn.textContent = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  }
  btn.onclick = function () {
    var next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('mnemo-theme', next);
    sync();
  };
  sync();
})();
