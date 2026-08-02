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

    const items = this.querySelectorAll('.steps-carousel__item');
    if (items.length === 0) return;

    // 1件分の幅（gap 含む）。端数が出ると scroll-snap が中途半端な位置で
    // 止まるため、実測値をそのまま使う
    const gap = parseFloat(getComputedStyle(this.track).columnGap) || 0;
    const distance = items[0].getBoundingClientRect().width + gap;

    // scrollBy は使わない。scroll-snap-type が mandatory のとき、Chrome は
    // 相対スクロールを現在のスナップ位置へ巻き戻すことがあり、末尾からの
    // 「前へ」がまったく動かない。送り先を明示する scrollTo なら効く
    const maximum = this.track.scrollWidth - this.track.clientWidth;
    const current = Math.round(this.track.scrollLeft / distance);
    const step = button.dataset.direction === 'next' ? 1 : -1;
    const index = Math.min(Math.max(current + step, 0), items.length - 1);

    this.track.scrollTo({
      left: Math.min(index * distance, maximum),
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
