class StepsCarousel extends HTMLElement {
  connectedCallback() {
    this.track = this.querySelector('.steps-carousel__track');
    if (!this.track) return;

    // 送りボタンは JS が動いて初めて意味を持つので、ここで表示する
    this.controls = this.closest('.steps-carousel')?.querySelector('.steps-carousel__controls');
    if (this.controls) {
      this.controls.hidden = false;
      this.controls.addEventListener('click', this.handleControlClick);
    }

    this.track.addEventListener('scroll', this.updateControlState, { passive: true });
    window.addEventListener('resize', this.updateControlState);
    this.updateControlState();
  }

  disconnectedCallback() {
    this.controls?.removeEventListener('click', this.handleControlClick);
    this.track?.removeEventListener('scroll', this.updateControlState);
    window.removeEventListener('resize', this.updateControlState);
  }

  handleControlClick = (event) => {
    const button = event.target.closest('[data-direction]');
    if (!button) return;

    const item = this.querySelector('.steps-carousel__item');
    if (!item) return;

    // 1件分の幅（gap 含む）だけ送る。端数が出ると scroll-snap が
    // 中途半端な位置で止まるため、実測値をそのまま使う
    const gap = parseFloat(getComputedStyle(this.track).columnGap) || 0;
    const distance = item.getBoundingClientRect().width + gap;

    this.track.scrollBy({
      left: button.dataset.direction === 'next' ? distance : -distance,
      behavior: 'smooth',
    });
  };

  updateControlState = () => {
    if (!this.controls) return;

    const { scrollLeft, scrollWidth, clientWidth } = this.track;
    // 小数のズレで最後まで送っても disabled にならないことがあるため 1px 許容する
    const atStart = scrollLeft <= 1;
    const atEnd = scrollLeft + clientWidth >= scrollWidth - 1;

    this.controls.querySelector('[data-direction="previous"]').disabled = atStart;
    this.controls.querySelector('[data-direction="next"]').disabled = atEnd;
    // スクロールが不要なときはボタン自体を隠す
    this.controls.hidden = scrollWidth <= clientWidth + 1;
  };
}

customElements.define('steps-carousel', StepsCarousel);
