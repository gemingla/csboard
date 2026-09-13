/* cs榜 · CSBOARD — 交互脚本（原生 JS，无外部依赖） */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- 数字滚动（围观指数，带缓出） ---- */
  function animateNumbers() {
    document.querySelectorAll("[data-count]").forEach(function (el) {
      var target = parseInt(el.getAttribute("data-count"), 10) || 0;
      if (reduceMotion || target <= 0) {
        el.textContent = target.toLocaleString("zh-CN");
        return;
      }
      var duration = 900;
      var start = null;
      function tick(ts) {
        if (start === null) start = ts;
        var p = Math.min(1, (ts - start) / duration);
        var eased = 1 - Math.pow(1 - p, 3);            /* easeOutCubic：丝滑收尾 */
        var value = Math.round(target * eased);
        el.textContent = value.toLocaleString("zh-CN");
        if (p < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }

  /* ---- 交错入场：滚动到视口时依次浮现 ---- */
  function bindReveal() {
    var items = document.querySelectorAll(
      ".rank-row, .board-section, .stage-board, .detail-card, .admin-wrap > *, .stat, .table, .form-card, .footer"
    );
    if (!items.length) return;
    if (reduceMotion || !("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.classList.add("revealed"); });
      return;
    }
    items.forEach(function (el, i) {
      el.classList.add("reveal");
      el.style.transitionDelay = Math.min(i % 12, 11) * 45 + "ms";
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
    items.forEach(function (el) { io.observe(el); });
  }

  /* ---- 光斑跟随鼠标（背景呼吸感） ---- */
  function bindAurora() {
    if (reduceMotion) return;
    var x = 50, y = 20, tx = 50, ty = 20, raf = null;
    document.addEventListener("mousemove", function (e) {
      tx = (e.clientX / window.innerWidth) * 100;
      ty = (e.clientY / window.innerHeight) * 100;
      if (!raf) raf = requestAnimationFrame(loop);
    });
    function loop() {
      x += (tx - x) * 0.045;                            /* 缓动跟随，丝滑不抖 */
      y += (ty - y) * 0.045;
      document.body.style.setProperty("--mx", x.toFixed(2) + "%");
      document.body.style.setProperty("--my", y.toFixed(2) + "%");
      raf = (Math.abs(tx - x) > 0.2 || Math.abs(ty - y) > 0.2) ? requestAnimationFrame(loop) : null;
    }
  }

  /* ---- 按钮涟漪 ---- */
  function bindRipple() {
    if (reduceMotion) return;
    document.addEventListener("click", function (e) {
      var btn = e.target.closest(".btn, .heat-btn");
      if (!btn) return;
      var rect = btn.getBoundingClientRect();
      var size = Math.max(rect.width, rect.height);
      var span = document.createElement("span");
      span.className = "ripple";
      span.style.width = span.style.height = size + "px";
      span.style.left = (e.clientX - rect.left - size / 2) + "px";
      span.style.top = (e.clientY - rect.top - size / 2) + "px";
      if (getComputedStyle(btn).position === "static") btn.style.position = "relative";
      btn.style.overflow = "hidden";
      btn.appendChild(span);
      setTimeout(function () { span.remove(); }, 620);
    });
  }

  /* ---- 进度条：顶部滚动指示 ---- */
  function bindScrollProgress() {
    var bar = document.createElement("div");
    bar.className = "scroll-progress";
    document.body.appendChild(bar);
    function update() {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      var p = h > 0 ? Math.min(1, window.scrollY / h) : 0;
      bar.style.transform = "scaleX(" + p + ")";
    }
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  }

  /* ---- 条款弹窗 ---- */
  function bindTerms() {
    var overlay = document.getElementById("terms-overlay");
    if (!overlay) return;
    document.getElementById("terms-accept")?.addEventListener("click", function () {
      overlay.classList.add("hidden");
      try {
        sessionStorage.setItem("bb_terms_ok", "1");
        if (window.location.hash === "#terms") history.replaceState(null, "", window.location.pathname);
      } catch (e) { /* 忽略隐私模式 */ }
    });
    document.getElementById("terms-reject")?.addEventListener("click", function () {
      window.location.href = "/terms-rejected";
    });
  }

  /* ---- 左右献唱轮流播放（一个唱，另一个暂停；20 秒一换） ---- */
  function bindDuet() {
    var vids = Array.prototype.slice.call(document.querySelectorAll(".side-video video"));
    if (vids.length < 2) return;
    var DURATION = 20000;
    var current = 0;
    var timer = null;
    var started = false;

    function show(idx) {
      current = idx;
      vids.forEach(function (v, i) {
        if (i === idx) {
          v.play().catch(function () { /* 等用户手势 */ });
          v.classList.add("is-singing");
        } else {
          v.pause();
          v.currentTime = 0;
          v.classList.remove("is-singing");
        }
      });
      clearInterval(timer);
      timer = setInterval(function () { show((current + 1) % vids.length); }, DURATION);
    }

    function begin() {
      if (started) return;
      started = true;
      var overlay = document.getElementById("duet-cta");
      if (overlay) {
        overlay.classList.add("fade-out");
        setTimeout(function () { overlay.remove(); }, 320);
      }
      show(0);
    }

    vids.forEach(function (v, i) {
      v.addEventListener("click", function () { begin(); show(i); });
      v.addEventListener("play", function () {
        vids.forEach(function (o, j) {
          if (j !== i && !o.paused) o.pause();
          o.classList.toggle("is-singing", j === i);
        });
      });
    });
    document.getElementById("duet-cta")?.addEventListener("click", begin);
    /* 不自动开播：等用户点击后才开始 */
  }

  /* ---- 表单增强（提交前确认） ---- */
  function bindForms() {
    document.querySelectorAll("form[data-confirm]").forEach(function (f) {
      f.addEventListener("submit", function (e) {
        if (!window.confirm(f.getAttribute("data-confirm"))) e.preventDefault();
      });
    });
  }

  /* ---- 键盘彩蛋：B-E-A-S-T ---- */
  function bindEasterEgg() {
    var seq = ["b", "e", "a", "s", "t"];
    var idx = 0;
    document.addEventListener("keydown", function (ev) {
      var k = (ev.key || "").toLowerCase();
      if (k === seq[idx]) {
        idx += 1;
        if (idx === seq.length) {
          idx = 0;
          window.alert("🐺 你找到彩蛋了！\n\n「说他是畜牲是玩笑，行好事才配得上这榜。」\n—— 本系统开发组留言");
        }
      } else {
        idx = k === seq[0] ? 1 : 0;
      }
    });
  }

  /* ---- 榜单行：色带跟随 hover ---- */
  function bindRowGlow() {
    if (reduceMotion) return;
    document.querySelectorAll(".rank-row").forEach(function (row) {
      row.addEventListener("mousemove", function (e) {
        var r = row.getBoundingClientRect();
        row.style.setProperty("--hx", ((e.clientX - r.left) / r.width * 100).toFixed(1) + "%");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    animateNumbers();
    bindReveal();
    bindAurora();
    bindRipple();
    bindScrollProgress();
    bindRowGlow();
    bindTerms();
    bindDuet();
    bindForms();
    bindEasterEgg();
    document.querySelectorAll(".flash").forEach(function (el) {
      setTimeout(function () { el.style.opacity = "0"; el.style.transition = "opacity .4s"; }, 3000);
      setTimeout(function () { el.remove(); }, 3600);
    });
  });
})();
