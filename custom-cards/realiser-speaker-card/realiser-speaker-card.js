/* Realiser A16 Speaker Grid Custom Card for Home Assistant */

class RealiserSpeakerCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error('You need to define an entity');
    }
    this._config = config;
    this._entity = config.entity;
    this._speakerData = {};
    this._mode = 'MUTE'; // Default mode
    this._hass = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  get hass() {
    return this._hass;
  }

  _update() {
    if (!this._hass || !this._hass.states) {
      return;
    }

    const stateObj = this._hass.states[this._entity];
    if (!stateObj) {
      return;
    }

    // Parse speaker data from sensor attributes
    const attributes = stateObj.attributes;
    this._mode = (attributes.mode || 'MUTE').toUpperCase();
    this._speakerData = attributes.speakers || {};

    // Force re-render
    this._render();
  }

  _toggleSpeaker(speakerId) {
    if (!this._hass) return;

    const entityId = `switch.realiser_a16_speaker_${speakerId}`;
    const stateObj = this._hass.states[entityId];

    if (stateObj && stateObj.attributes.metadata && stateObj.attributes.metadata.lovelace_card) {
      // Card is managing this entity, count toggle or rely on toggle service
    }

    // Call the toggle service for the speaker switch
    this._hass.callService('homeassistant', 'toggle', {
      entity_id: entityId,
    }).catch(err => {
      console.error('Failed to toggle speaker:', err);
    });
  }

  _toggleAll() {
    if (!this._hass) return;

    const entityId = 'switch.realiser_a16_all_solo';
    this._hass.callService('homeassistant', 'toggle', {
      entity_id: entityId,
    }).catch(err => {
      console.error('Failed to toggle all speakers:', err);
    });
  }

  _getSpeakerColor(speakerId) {
    // Speaker types based on ID - following the same layout as example
    const speakerColors = {
      // LFE (subwoofers)
      4: 'lfe', 12: 'lfe', 51: 'lfe', 52: 'lfe',
      43: 'lfe',  // Lrs2? Actually not LFE - but let's keep mapping
      // Floor speakers (front, center, side, rear)
      1: 'floor', 2: 'floor', 3: 'floor',
      5: 'floor', 6: 'floor', 7: 'floor', 8: 'floor',
      9: 'floor', 10: 'floor', 13: 'floor', 14: 'floor',
      15: 'floor', 16: 'floor', 17: 'floor', 18: 'floor',
      39: 'floor', 40: 'floor', 41: 'floor', 42: 'floor',
      11: 'floor', // Cr
      // Height speakers (atmos height)
      25: 'height', 26: 'height', 27: 'height', 28: 'height',
      29: 'height', 30: 'height', 45: 'height', 46: 'height',
      47: 'height', 48: 'height',
      // Overhead speakers
      22: 'overhead', 23: 'overhead', 24: 'overhead',
      31: 'overhead', 32: 'overhead', 33: 'overhead', 34: 'overhead',
      35: 'overhead', 36: 'overhead',
      // Under speakers (though not sure if any - these would be under ear level)
      19: 'under', 20: 'under', 21: 'under',
      49: 'under', 50: 'under',
    };

    return speakerColors[speakerId] || 'floor';
  }

  _createButton(speakerId, name, visible, active) {
    if (!visible) {
      // Create hidden slot
      const hiddenBtn = document.createElement('button');
      hiddenBtn.className = 'grid-item hidden';
      hiddenBtn.id = speakerId.toString();
      hiddenBtn.style.opacity = '0.05';
      hiddenBtn.style.pointerEvents = 'none';
      return hiddenBtn;
    }

    const btn = document.createElement('button');
    btn.className = 'grid-item';
    btn.id = speakerId.toString();
    btn.textContent = name;

    // Add color class based on speaker type
    const colorClass = this._getSpeakerColor(speakerId);
    btn.classList.add(colorClass);

    // Set active state styling
    if (active) {
      btn.classList.add('active');
      btn.style.backgroundColor = this._getActiveColor(colorClass);
    }

    btn.addEventListener('click', () => this._toggleSpeaker(speakerId));
    return btn;
  }

  _getActiveColor(baseColor) {
    // Return a brighter/more saturated version for active state
    const colors = {
      floor: '#2d6b2d',    // Darker green
      height: '#cc7a00',   // Darker orange
      overhead: '#800080', // Darker violet
      under: '#b39700',    // Darker yellow
      lfe: '#b30000'       // Darker red
    };
    return colors[baseColor] || '#2d6b2d';
  }

  _render() {
    // Clear container
    while (this.firstChild) {
      this.removeChild(this.firstChild);
    }

    // Create main container
    const container = document.createElement('div');
    container.className = 'realiser-speaker-container';

    // Header with title and power/info
    const header = document.createElement('div');
    header.className = 'realiser-header';
    header.innerHTML = `
      <div class="realiser-title">Speaker Grid</div>
      <div class="realiser-mode">Mode: ${this._mode}</div>
    `;
    container.appendChild(header);

    // Create grid container (9 columns)
    const gridContainer = document.createElement('div');
    gridContainer.className = 'realiser-grid-container';
    gridContainer.style.gridTemplateColumns = 'repeat(9, 1fr)';

    // Define grid layout based on example web - 7 rows worth of buttons
    // Row 1: SW L Lc Lsc C Rsc Rc R SW2
    const row1 = [4, 1, 17, 37, 3, 38, 18, 2, 12];
    // Row 2: Lw Lhw Lh -- Ch -- Rh Rhw Rw
    const row2 = [13, 45, 25, null, 22, null, 26, 46, 14];
    // Row 3: Ls1 -- Ltf Lu Cu Ru Rtf -- Rs1
    const row3 = [39, null, 31, 19, 21, 20, 32, null, 40];
    // Row 4: Lss Lhs Ltm -- T -- Rtm Rhs Rss
    const row4 = [9, 27, 33, null, 24, null, 34, 28, 10];
    // Row 5: Ls Lhs1 Ltr -- -- -- Rtr Rhs1 Rs
    const row5 = [5, 47, 35, null, null, null, 36, 48, 6];
    // Row 6: Lrs1 -- Lhr Lbu Chr Rbu Rhr -- Rrs1
    const row6 = [41, null, 29, 49, 23, 50, 30, null, 42];
    // Row 7: SW Lb Lrs2 Lbs Cr Rbs Rrs2 Rb SW
    const row7 = [51, 7, 43, 15, 11, 16, 44, 8, 52];

    const gridLayout = [...row1, ...row2, ...row3, ...row4, ...row5, ...row6, ...row7];

    // Create grid items
    gridLayout.forEach(speakerId => {
      const spkData = speakerId ? this._speakerData[speakerId] : null;
      const name = spkData ? spkData.name : (speakerId ? `Spk${speakerId}` : '');
      const visible = spkData ? spkData.visible : (speakerId ? false : false);
      const active = spkData ? spkData.state === 'active' : false;

      const btn = this._createButton(speakerId, name, visible, active);
      gridContainer.appendChild(btn);
    });

    container.appendChild(gridContainer);

    // MUTE/SOLO label and ALL button
    const controlRow = document.createElement('div');
    controlRow.className = 'realiser-control-row';
    controlRow.innerHTML = `
      <div class="realiser-mute-label">MUTE/SOLO</div>
      <button class="realiser-all-btn">ALL</button>
    `;

    const allBtn = controlRow.querySelector('.realiser-all-btn');
    allBtn.addEventListener('click', () => this._toggleAll());

    // Style the ALL button based on mode
    if (this._mode === 'SOLO') {
      allBtn.classList.add('active');
      allBtn.style.backgroundColor = '#3e8e41';
    }

    container.appendChild(controlRow);

    this.appendChild(container);
  }

  // Custom card lifecycle
  connectedCallback() {
    // Shadow DOM for encapsulation
    this.attachShadow({ mode: 'open' });
    this._injectStyles();
  }

  disconnectedCallback() {
    // Cleanup
  }

  _injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .realiser-speaker-container {
        font-family: Arial, sans-serif;
        background-color: #f4f4f9;
        padding: 20px;
        border-radius: 10px;
        max-width: 800px;
        margin: 0 auto;
      }

      .realiser-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
      }

      .realiser-title {
        font-size: 1.5em;
        font-weight: bold;
        color: #333;
      }

      .realiser-mode {
        font-weight: bold;
        color: #666;
        padding: 5px 10px;
        background: #ddd;
        border-radius: 5px;
      }

      .realiser-grid-container {
        display: grid;
        gap: 2px;
        max-width: 600px;
        margin: 0 auto 15px;
      }

      .realiser-grid-container .grid-item {
        aspect-ratio: 1;
        border: none;
        cursor: pointer;
        border-radius: 5px;
        transition: background-color 0.3s ease, transform 0.1s ease;
        font-size: 14px;
        font-weight: bold;
        color: black;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: auto;
        padding: 0;
      }

      .realiser-grid-container .grid-item:hover {
        filter: brightness(1.2);
        transform: scale(1.05);
      }

      /* Speaker type colors */
      .realiser-grid-container .floor {
        background-color: #4CAF50;
      }

      .realiser-grid-container .height {
        background-color: orange;
      }

      .realiser-grid-container .overhead {
        background-color: violet;
      }

      .realiser-grid-container .under {
        background-color: yellow;
      }

      .realiser-grid-container .lfe {
        background-color: red;
      }

      /* Active state */
      .realiser-grid-container .grid-item.active {
        filter: brightness(0.7);
      }

      .realiser-grid-container .grid-item.active.floor {
        background-color: #2d6b2d !important;
      }

      .realiser-grid-container .grid-item.active.height {
        background-color: #cc7a00 !important;
      }

      .realiser-grid-container .grid-item.active.overhead {
        background-color: #800080 !important;
      }

      .realiser-grid-container .grid-item.active.under {
        background-color: #b39700 !important;
      }

      .realiser-grid-container .grid-item.active.lfe {
        background-color: #b30000 !important;
      }

      /* Hidden slots */
      .realiser-grid-container .grid-item.hidden {
        opacity: 0.05;
        pointer-events: none;
        background-color: #ccc !important;
      }

      /* Control row */
      .realiser-control-row {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 15px;
        margin-top: 10px;
      }

      .realiser-mute-label {
        font-weight: bold;
        color: #666;
      }

      .realiser-all-btn {
        padding: 10px 20px;
        font-size: 16px;
        border: none;
        border-radius: 5px;
        background-color: #4CAF50;
        color: white;
        cursor: pointer;
        transition: background-color 0.3s ease;
      }

      .realiser-all-btn:hover {
        background-color: #45a049;
      }

      .realiser-all-btn.active {
        background-color: #3e8e41;
      }
    `;
    this.shadowRoot.appendChild(style);
  }
}

// Define the custom element
customElements.define('realiser-speaker-card', RealiserSpeakerCard);

// Inform Home Assistant about the custom card
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'realiser-speaker-card',
  name: 'Realiser Speaker Card',
  description: 'Custom card displaying Realiser A16 speaker grid'
});