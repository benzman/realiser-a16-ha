/* Realiser A16 Speaker Grid Custom Card for Home Assistant */

class RealiserSpeakerCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error('You need to define an entity');
    }
    this._config = config;
    this._entity = config.entity;
    this._title = config.title || 'Speaker Grid';
    this._speakerData = {};
    this._mode = 'MUTE';
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  _update() {
    if (!this._hass || !this._hass.states) return;

    const stateObj = this._hass.states[this._entity];
    if (!stateObj) return;

    const attributes = stateObj.attributes || {};
    this._mode = (attributes.mode || 'MUTE').toUpperCase();
    this._speakerData = attributes.speakers || {};

    this._render();
  }

  _toggleSpeaker(speakerId) {
    if (!this._hass) return;
    const id = parseInt(speakerId);
    
    const entityId = `switch.realiser_a16_speaker_${id}`;
    const state = this._hass.states[entityId];

    if (!state) {
      console.warn(`Speaker ${speakerId} switch not found: ${entityId}`);
      return;
    }
    
    this._hass.callService('homeassistant', 'toggle', { entity_id: entityId })
      .then(() => console.log('Toggle successful'))
      .catch(err => console.error('Toggle error:', err));
  }

  _toggleAll() {
    if (!this._hass) return;
    this._hass.callService('homeassistant', 'toggle', { entity_id: 'switch.realiser_a16_all_solo' });
  }

  _refresh() {
    if (!this._hass) return;
    this._hass.callService('realiser_a16', 'refresh_speakers');
  }

  _getSpeakerColor(speakerId) {
    const floor = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18];
    const height = [25,26,27,28,29,30,45,46,47,48];
    const overhead = [22,23,24,31,32,33,34,35,36];
    if (floor.includes(speakerId)) return '#4CAF50';
    if (height.includes(speakerId)) return '#FF9800';
    if (overhead.includes(speakerId)) return '#9C27B0';
    return '#607D8B';
  }

  _render() {
    this.innerHTML = '';
    
    const container = document.createElement('div');
    container.style.cssText = 'font-family: Arial; padding: 10px; background: #f5f5f5; border-radius: 10px;';
    
    // Header
    const header = document.createElement('div');
    header.style.cssText = 'display: flex; justify-content: space-between; margin-bottom: 10px;';
    header.innerHTML = `
      <div style="font-size: 1.2em; font-weight: bold;">${this._title}</div>
      <div style="padding: 5px 10px; background: #ddd; border-radius: 5px;">Mode: ${this._mode}</div>
    `;
    container.appendChild(header);
    
    // Refresh button
    const refreshBtn = document.createElement('button');
    refreshBtn.textContent = '🔄 Refresh';
    refreshBtn.style.cssText = 'padding: 8px 16px; margin-bottom: 10px; cursor: pointer; border: none; border-radius: 5px; background: #2196F3; color: white;';
    refreshBtn.onclick = () => this._refresh();
    container.appendChild(refreshBtn);
    
    // Speaker grid (9 columns)
    const grid = document.createElement('div');
    grid.style.cssText = 'display: grid; grid-template-columns: repeat(9, 1fr); gap: 3px; max-width: 500px; margin: 0 auto;';
    
    // Grid layout
    const layout = [
      [4, 1, 17, 37, 3, 38, 18, 2, 12],
      [13, 45, 25, null, 22, null, 26, 46, 14],
      [39, null, 31, 19, 21, 20, 32, null, 40],
      [9, 27, 33, null, 24, null, 34, 28, 10],
      [5, 47, 35, null, null, null, 36, 48, 6],
      [41, null, 29, 49, 23, 50, 30, null, 42],
      [51, 7, 43, 15, 11, 16, 44, 8, 52]
    ];
    
    for (const row of layout) {
      for (const speakerId of row) {
        const cell = document.createElement('div');
        
        if (speakerId === null) {
          cell.style.cssText = 'aspect-ratio: 1; opacity: 0.1;';
        } else {
          const spk = this._speakerData[speakerId] || {};
          const name = spk.name || `S${speakerId}`;
          const visible = spk.visible !== false;
          const active = spk.state === 'active';
          
          const btn = document.createElement('button');
          btn.textContent = name;
          btn.style.cssText = `
            aspect-ratio: 1;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 11px;
            font-weight: bold;
            color: white;
            background: ${visible ? this._getSpeakerColor(speakerId) : '#ccc'};
            opacity: ${visible ? (active ? 1 : 0.6) : 0.3};
          `;
          
          if (visible) {
            btn.onclick = () => this._toggleSpeaker(speakerId);
          }
          
          cell.appendChild(btn);
        }
        grid.appendChild(cell);
      }
    }
    container.appendChild(grid);
    
    // ALL button
    const allBtn = document.createElement('button');
    allBtn.textContent = 'ALL';
    allBtn.style.cssText = `
      margin-top: 10px;
      padding: 10px 30px;
      font-size: 14px;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      background: ${this._mode === 'SOLO' ? '#4CAF50' : '#FF9800'};
      color: white;
    `;
    allBtn.onclick = () => this._toggleAll();
    container.appendChild(allBtn);
    
    this.appendChild(container);
  }
}

customElements.define('realiser-speaker-card', RealiserSpeakerCard);
