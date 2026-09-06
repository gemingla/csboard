/* 畜牲榜 · BeastBoard — 交互脚本（原生 JS，无外部依赖） */
(function () {
  "use strict";

  /* ---- 数字滚动（围观指数） ---- */
  function animateNumbers() {
    document.querySelectorAll("[data-count]").forEach(function (el) {
      var target = parseInt(el.getAttribute("data-count"), 10) || 0;
      var state = 0;
      var step = Math.max(1, Math.ceil(target / 60));
      var timer = setInterval(function () {
        state += step;
        if (state >= target) {
          state = target;
          clearInterval(timer);
        }
        el.textContent = state.toLocaleString("zh-CN");
      }, 18);
    });
  }

  /* ---- 条款弹窗（js 控制显隐，默认由服务端条件渲染） ---- */
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

  /* ---- 视频卡片：点击切换/播放 ---- */
  function bindVideos() {
    document.querySelectorAll(".video-item video").forEach(function (v) {
      v.addEventListener("click", function () {
        if (v.paused) {
          document.querySelectorAll("video").forEach(function (o) { if (o !== v) o.pause(); });
          v.play();
        } else {
          v.pause();
        }
      });
    });
  }

  /* ---- 表单简单增强（提交前确认 / 字数统计） ---- */
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

  document.addEventListener("DOMContentLoaded", function () {
    animateNumbers();
    bindTerms();
    bindVideos();
    bindForms();
    bindEasterEgg();
    /* 闪现消息自动消失 */
    document.querySelectorAll(".flash").forEach(function (el) {
      setTimeout(function () { el.style.opacity = "0"; el.style.transition = "opacity .4s"; }, 3000);
      setTimeout(function () { el.remove(); }, 3600);
    });
  });
})();
