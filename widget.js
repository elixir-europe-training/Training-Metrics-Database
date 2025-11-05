(function (global) {
  /**
   * Base endpoint for question set summary statistics.
   * The request URL is composed as `${DEFAULT_BASE_URL}${questionSet}` unless a custom `endpoint` is provided.
   */
  const DEFAULT_BASE_URL = 'https://tmd.elixir-europe.org/metrics/set/';
  const CHART_JS_CDN = 'https://cdn.jsdelivr.net/npm/chart.js';

  /**
   * Default configuration for the widget. Settings can be overridden via the `TMDWidget` factory function.
   */
  const DEFAULT_OPTIONS = {
    questionSet: 'quality',
    chartType: 'bar',
    questions: null,
    dataScope: 'all',
    endpoint: null,
    colors: null,
  };

  /**
   * Resolve a DOM node from a selector string or return the node if one is provided.
   *
   * @param {string | HTMLElement} target
   * @returns {HTMLElement | null}
   */
  function resolveContainer(target) {
    if (!target) {
      return null;
    }
    if (typeof target === 'string') {
      return document.querySelector(target);
    }
    if (target instanceof HTMLElement) {
      return target;
    }
    return null;
  }

  /**
   * Normalise the API payload into an array of questions with aggregated counts.
   *
   * @param {unknown} payload
   * @param {Set<string> | null} questionFilter
   * @returns {Array<{ id: string, label: string, aggregated: Record<string, number> }>}
   */
  function normalisePayload(payload, questionFilter) {
    const values = Array.isArray(payload?.values) ? payload.values : [];
    return values.reduce((acc, entry) => {
      const id = entry?.id || entry?.slug || entry?.label;
      if (!id || (questionFilter && !questionFilter.has(id))) {
        return acc;
      }

      const options = Array.isArray(entry?.options) ? entry.options : [];
      const aggregated = options.reduce((map, option) => {
        const optionLabel = option?.label || option?.id;
        if (!optionLabel) {
          return map;
        }
        const count = Number(option?.count ?? 0);
        map[optionLabel] = Number.isFinite(count) ? count : 0;
        return map;
      }, {});

      acc.push({
        id,
        label: entry?.label || entry?.title || id,
        aggregated,
      });
      return acc;
    }, []);
  }

  /**
   * Default colourway borrowed from Plotly (used by the in-app reports) so the widget matches
   * the styling on `/report/set/<question-set>`.
   */
  const DEFAULT_COLORWAY = [
    '#1f77b4',
    '#ff7f0e',
    '#2ca02c',
    '#d62728',
    '#9467bd',
    '#8c564b',
    '#e377c2',
    '#7f7f7f',
    '#bcbd22',
    '#17becf',
  ];

  /**
   * Cycle through the Plotly colourway to generate chart colours.
   *
   * @param {number} size
   * @param {string[] | null} overrideColors
   * @returns {string[]}
   */
  function buildPalette(size, overrideColors) {
    if (size <= 0) {
      return [];
    }

    const source =
      Array.isArray(overrideColors) && overrideColors.length > 0
        ? overrideColors
        : DEFAULT_COLORWAY;

    const palette = [];
    for (let index = 0; index < size; index += 1) {
      palette.push(source[index % source.length]);
    }
    return palette;
  }

  let chartJsLoader = null;

  /**
   * Ensure Chart.js is available globally, loading it from the CDN if necessary.
   *
   * @returns {Promise<void>}
   */
  function ensureChartJs() {
    if (typeof global.Chart !== 'undefined') {
      return Promise.resolve();
    }

    if (!chartJsLoader) {
      chartJsLoader = new Promise((resolve, reject) => {
        const existingScript = document.querySelector(`script[src="${CHART_JS_CDN}"]`);
        if (existingScript) {
          existingScript.addEventListener('load', () => resolve());
          existingScript.addEventListener('error', () =>
            reject(new Error('Failed to load Chart.js'))
          );
          return;
        }

        const script = document.createElement('script');
        script.src = CHART_JS_CDN;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('Failed to load Chart.js'));
        document.head.appendChild(script);
      });
    }

    return chartJsLoader.then(() => {
      if (typeof global.Chart === 'undefined') {
        throw new Error('Chart.js failed to initialise.');
      }
    });
  }

  /**
   * Render a single question chart inside the container.
   *
   * @param {HTMLElement} container
   * @param {{ id: string, label: string, aggregated: Record<string, number> }} question
   * @param {'bar' | 'pie'} chartType
   * @param {string[] | null} colors
   * @returns {Chart}
   */
  function renderQuestionChart(container, question, chartType, colors) {
    const labels = Object.keys(question.aggregated);
    const values = labels.map((label) => question.aggregated[label]);

    const wrapper = document.createElement('section');
    wrapper.className = 'tmd-widget-question';

    const heading = document.createElement('h2');
    heading.className = 'tmd-widget-question__title';
    heading.textContent = question.label;
    wrapper.appendChild(heading);

    const canvasWrapper = document.createElement('div');
    canvasWrapper.className = 'tmd-widget-chart';
    canvasWrapper.style.minHeight = chartType === 'pie' ? '320px' : '360px';
    const canvas = document.createElement('canvas');
    canvasWrapper.appendChild(canvas);
    wrapper.appendChild(canvasWrapper);
    container.appendChild(wrapper);

    const palette = buildPalette(labels.length, colors);
    const isPie = chartType === 'pie';

    return new Chart(canvas.getContext('2d'), {
      type: chartType,
      data: {
        labels,
        datasets: [
          {
            label: question.label,
            data: values,
            backgroundColor: palette,
            borderWidth: isPie ? 0 : 1,
            borderColor: isPie ? undefined : 'rgba(0, 0, 0, 0.1)',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
          },
        },
        scales: isPie
          ? {}
          : {
              y: {
                beginAtZero: true,
                ticks: {
                  precision: 0,
                },
                title: {
                  display: true,
                  text: 'Responses',
                },
              },
              x: {
                ticks: {
                  maxRotation: 45,
                  minRotation: 0,
                  autoSkip: false,
                },
              },
            },
      },
    });
  }

  /**
   * Clear previous widget state, destroy Chart instances, and show a message.
   *
   * @param {HTMLElement} container
   * @param {string} message
   */
  function showMessage(container, message) {
    if (Array.isArray(container._tmdCharts)) {
      container._tmdCharts.forEach((chartInstance) => chartInstance.destroy());
    }
    container._tmdCharts = [];
    container.innerHTML = '';

    const paragraph = document.createElement('p');
    paragraph.className = 'tmd-widget-message';
    paragraph.textContent = message;
    container.appendChild(paragraph);
  }

  /**
   * Entry point exposed globally.
   *
   * @param {Object} options
   * @param {string | HTMLElement} options.container - Selector or element that will host the widget.
   * @param {'all' | 'node'} [options.dataScope] - Scope of data to request; currently only `all` is supported.
   * @param {string} [options.questionSet] - Question set slug to request.
   * @param {string[]} [options.questions] - Optional subset of question IDs to include.
   * @param {'bar' | 'pie'} [options.chartType] - Desired chart type.
   * @param {string} [options.endpoint] - Full endpoint override; otherwise derived from question set.
   * @param {string[]} [options.colors] - Optional array of CSS colour strings applied cyclically to chart segments.
   * @returns {Promise<void>}
   */
  async function TMDWidget(options) {
    await ensureChartJs();

    const settings = { ...DEFAULT_OPTIONS, ...options };
    const container = resolveContainer(settings.container);
    if (!container) {
      throw new Error('TMDWidget requires a valid container element.');
    }

    showMessage(container, 'Loading metrics…');

    const questionFilter =
      Array.isArray(settings.questions) && settings.questions.length > 0
        ? new Set(settings.questions)
        : null;

    const requestUrl =
      settings.endpoint ||
      `${DEFAULT_BASE_URL}${encodeURIComponent(settings.questionSet)}`;

    let response;
    try {
      response = await fetch(requestUrl, { credentials: 'omit' });
    } catch (error) {
      showMessage(container, 'Unable to reach the Training Metrics Database.');
      throw error;
    }

    if (!response.ok) {
      showMessage(container, 'Failed to load metrics data.');
      throw new Error(`TMDWidget request failed with status ${response.status}`);
    }

    const payload = await response.json();
    const questions = normalisePayload(payload, questionFilter);
    if (questions.length === 0) {
      showMessage(container, 'No metrics available for the requested configuration.');
      return;
    }

    if (Array.isArray(container._tmdCharts)) {
      container._tmdCharts.forEach((chartInstance) => chartInstance.destroy());
    }
    container._tmdCharts = [];
    container.innerHTML = '';

    questions.forEach((question) => {
      const chartInstance = renderQuestionChart(
        container,
        question,
        settings.chartType,
        settings.colors
      );
      container._tmdCharts.push(chartInstance);
    });
  }

  global.TMDWidget = TMDWidget;
})(window);
