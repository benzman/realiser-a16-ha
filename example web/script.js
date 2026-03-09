// WebSocket-Verbindung herstellen
let socket = new WebSocket(`ws://${location.hostname}:81/`);

socket.onopen = () => {
    console.log('WebSocket connected!');
    // Request initial speaker states
    sendCommand('NON_IRIP', 103); // Request speaker key visibility
    sendCommand('NON_IRIP', 104); // Request active speaker status
};
socket.onclose = () => console.log('WebSocket disconnected.');
socket.onerror = (error) => console.error('WebSocket error:', error);

// Global object to store the state of all channels
let channelStates = {};
let channels = {};
let channelLevels = {};
let UserA = {};
let UserB = {};
let Powerstatus = {};
let activeLevels = false;
let Assignments = {};

// Initialize the state for all channels
for (let i = 0; i <= 52; i++) {
    channelStates[`V${i < 10 ? '0' : ''}${i}`] = {
        defined: false, // Whether the channel is defined
        active: false, // Whether the channel is active
    };
}

// Function to update the state of channels
function updateChannelStates(data) {
    // Update the global state with the new data

    if (channelStates.ALL === 'SOLO') {
        Object.keys(channelStates).forEach(key => {
            if (channelStates[key].hasOwnProperty('active')) {
                channelStates[key].active = false;
            }
        });
    }
    Object.keys(data).forEach(key => {
        if (key.match(/^V\d{2}$/)) {
            const channelKey = key; // Definiere channelKey
            if (channelStates[channelKey]) {
                channelStates[channelKey].defined = true;
            } else {
                console.warn(`Unbekannter Kanal: ${key}`);
            }
        } else if (key.match(/^A\d{2}$/)) {
            const channelKey = `V${key.substring(1)}`; // Definiere channelKey
            if (channelStates[channelKey]) {
                channelStates[channelKey].active = true;
            } else {
                console.warn(`Unbekannter Kanal: ${channelKey}`);
            }
        } else if (key.match(/^M\d{2}$/)) {
            const channelKey = `V${key.substring(1)}`; // Definiere channelKey
            if (channelStates[channelKey]) {
                channelStates[channelKey].active = false;
            } else {
                console.warn(`Unbekannter Kanal: ${channelKey}`);
            }
        } else if (key === 'ALL') {
            // Update the global state
            channelStates.ALL = data[key];
        } else if (key === 'TEST') {
            // Update the test state
            channelStates.TEST = data[key];
        } else if (key === 'MODE') {
            // Update the mode state
            channelStates.MODE = data[key];
        } else {
            console.log(`Ignoriere Schlüssel: ${key}`);
        }
    });

    // Render the updated UI
    renderSpeakerGrid();
}

// Function to render the speaker grid based on the current state
function renderSpeakerGrid() {
    const ALL = channelStates.ALL || 'UNKNOWN'; // Global mode (active, MUTE, etc.)
    // console.log('Global Mode:', ALL);
    const mute_button = document.getElementById('MUTE/SOLO');
    if (ALL === 'SOLO') {
        mute_button.innerHTML = 'SOLO';
    } else if (ALL === 'MUTE') {
        mute_button.innerHTML = 'MUTE';
    }
    for (let i = 0; i <= 52; i++) {
        const channelKey = `V${i < 10 ? '0' : ''}${i}`;
        const button = document.getElementById(i.toString());
        if (!button) continue; // Skip if no button exists for this channel

        const channel = channelStates[channelKey];
        if (channel.defined) {
            button.classList.remove('hidden'); // Show defined channels
            // button.style.visibility = 'visible';

            if (channel.active) {
                button.classList.remove('greyscale');
                // button.style.filter = 'none'; // Full color for active channels
            } else {
                button.classList.add('greyscale');
                // button.style.filter = 'grayscale(100%)'; // Grayscale for inactive channels
            }
        } else {
            button.classList.add('hidden');
            // button.style.visibility = 'hidden'; // Hide undefined channels
        }
    }
}

// Function to update UserA data in the HTML
function updateUserAData() {
    Object.keys(UserA).forEach(key => {
        const element = document.getElementById(`${key}`);
        if (element) {
            element.textContent = UserA[key];
        }
    });
}

// Function to update UserB data in the HTML
function updateUserBData() {
    Object.keys(UserB).forEach(key => {
        const element = document.getElementById(`${key}`);
        if (element) {
            element.textContent = UserB[key];
        }
    });
}

function setActiveInputButton(activeId) {
    const buttons = document.querySelectorAll('.input-select');
    buttons.forEach(button => {
        if (button.id === activeId) {
            button.classList.remove('grey');
            // button.style.filter = 'none'; // Full color for active button
        } else {
            button.classList.add('grey');
            // button.style.filter = 'grayscale(100%)'; // Grayscale for inactive buttons
        }
    });
}

function setActivePAButton(activeId) {
    const buttons = document.querySelectorAll('.pa-select');
    buttons.forEach(button => {
        if (button.id === `PA${activeId}`) {
            button.classList.remove('grey');
            // button.style.filter = 'none'; // Full color for active button
        } else {
            button.classList.add('grey');
            // button.style.filter = 'grayscale(100%)'; // Grayscale for inactive buttons
        }
    });
}

function setActivePBButton(activeId) {
    const buttons = document.querySelectorAll('.pb-select');
    buttons.forEach(button => {
        if (button.id === `PB${activeId}`) {
            button.classList.remove('grey');
            // button.style.filter = 'none'; // Full color for active button
        } else {
            button.classList.add('grey');
            // button.style.filter = 'grayscale(100%)'; // Grayscale for inactive buttons
        }
    });
}

function handlePowerStatus() {
    const powerButton = document.getElementById('powerbutton');
    const blocker = document.getElementById('blocker');
    const powerStatusText = document.getElementById('powerstatus');
    if (Powerstatus.PWR === 'ON') {
        powerButton.style.backgroundColor = 'green';
        powerButton.style.color = 'white';
        powerButton.onclick = () => sendCommand('NON_IRIP', 14); // Set the command for power off
        blocker.style.display = 'none'; // Hide the blocker
        powerStatusText.innerText = '';
    }
    else if (Powerstatus.PWR === 'STANDBY') {
        powerButton.style.backgroundColor = 'red';
        powerButton.style.color = 'white';
        powerButton.onclick = () => sendCommand('NON_IRIP', 13); // Set the command for power on
        // blocker.style.display = 'block'; // Show the blocker
        blocker.style.display = 'flex';
        blocker.innerText = 'Power OFF';
    }
    else if (Powerstatus.PWR === 'BOOT') {
        powerButton.style.backgroundColor = 'yellow';
        powerButton.style.color = 'black';
        powerButton.onclick = () => sendCommand('NON_IRIP', 15); // Set the command for power status
        // blocker.style.display = 'block'; // Show the blocker
        blocker.style.display = 'flex';
        blocker.innerText = 'Booting...';
    }
}

function activateLevels() {
    // console.log('activateLevels');
    activeLevels = !activeLevels; // Toggle the activeLevels variable
    if (activeLevels === true) {
        activeLevelsID = setInterval(() => {
            sendCommand('NON_IRIP', 35); // Send a command to activate levels every second
        }, 1000);
        // Visuell und semantisch als aktiv markieren
        const levelsButton = document.getElementById('levels_active');
        if (levelsButton) {
            levelsButton.classList.add('active');
            levelsButton.classList.remove('grey');
            // optional: anzeigetext anpassen
            // levelsButton.innerText = 'Levels ON';
        }
    } else {
        clearInterval(activeLevelsID); // Clear the interval
        console.log('Levels deactivated');
        const levelTable = document.getElementById('level-table');
        if (levelTable) {
            const rows = levelTable.querySelectorAll('tr');
            rows.forEach(row => {
                const cell = row.querySelector('div.level');
                cell.style.width = 0; // Example: Change background color
                cell.innerText = ''; // Clear the inner text
            });
        }
        const levelsButton = document.getElementById('levels_active');
        if (levelsButton) {
            levelsButton.classList.remove('active');
            levelsButton.classList.add('grey');
            // optional: levelsButton.innerText = 'Levels OFF';
        }
        activeLevelsID = null;
    }
    // sendCommand('NON_IRIP', 35); // Send a command to activate levels
}

function assignments() {
    sendCommand('NON_IRIP', 17); 
}

function handleLevels() {
    Object.keys(channelLevels).forEach(element => {
        let channelKey = element;
        // console.log('channelKey:', channelKey);
        // const width = document.getElementById(channelKey);
        if (channelKey.startsWith('L')) {
            const channelNumber = channelKey.substring(1).padStart(2, '0'); // Extract the number and pad with leading zero if necessary
            const speaker = document.querySelector(`.ch${channelNumber} .level`);
            if (speaker) {
                const value = channelLevels[channelKey];
                speaker.style.width = `${value}%`;
                if (value > 0) {
                    speaker.innerText = value; // Set the inner text to the value
                } else {
                    speaker.innerText = ''; // Clear the inner text if value is 0
                }
            }
        } else {
            const speaker = document.querySelector(`.${channelKey} .level`);
            if (speaker) {
                const value = channelLevels[channelKey];
                speaker.style.width = `${value}%`;
                if (value > 0) {
                    speaker.innerText = value; // Set the inner text to the value
                } else {
                    speaker.innerText = ''; // Clear the inner text if value is 0
                }
            }
        }
    });
}

function handleAssignments() {
    Object.keys(Assignments).forEach(element => {
        let channelKey = element;
        if (channelKey.startsWith('ACH')) {
            const channelNumber = channelKey.substring(3).padStart(2, '0'); // Extract the number and pad with leading zero if necessary
            const speaker = document.querySelector(`.ch${channelNumber} .A`);
            if (speaker) {
                const value = Assignments[channelKey];
                speaker.textContent = value;
            }
        } else if (channelKey.startsWith('BCH')) {
            const channelNumber = channelKey.substring(3).padStart(2, '0'); // Extract the number and pad with leading zero if necessary
            const speaker = document.querySelector(`.ch${channelNumber} .B`);
            if (speaker) {
                const value = Assignments[channelKey];
                speaker.textContent = value;
            }
        }
    });
}

// WebSocket message handler
socket.onmessage = (event) => {
    const respDiv = document.getElementById('response-window');
    const respContent = document.getElementById('response-content');

    try {
        const data = JSON.parse(event.data);

        // Handle JSON responses (from internal commands)
        if (respDiv && respContent) {
            respContent.textContent = JSON.stringify(data, null, 2);
            respDiv.scrollTop = respDiv.scrollHeight;
        }

        // Process JSON data for speaker states, etc.
        // console.log('Received JSON data:', data);
        // channels = Object.keys(data).filter(key => key.match(/^V\d{2}$/) || key.match(/^A\d{2}$/) || key.match(/^M\d{2}$/) || key === 'ALL' || key === 'TEST' || key === 'MODE');
        channels = Object.keys(data).reduce((acc, key) => {
            if (key.match(/^V\d{2}$/) || key.match(/^A\d{2}$/) || key.match(/^M\d{2}$/) || key === 'ALL' || key === 'TEST' || key === 'MODE') {
            acc[key] = data[key];
            }
            return acc;
        }, {});
        // updateChannelStates(channels); // Update the state with the new data
        
        UserA = Object.keys(data).reduce((acc, key) => {
            if (key === 'AUR' || key === 'PA' || key === 'VA' || key === 'TRI' || key === 'AROOM' || key === 'ANAME' || key === 'ASPKR' || key === 'AQFILE' || key === 'AQNAME' || key === 'AQTYPE' || key === 'AQMOD' || key === 'ATACT' || key === 'IN' || key === 'DEC' || key === 'LM' || key === 'UMIX' || key === 'HTMODE' || key === 'LEG' || key === 'USER') {
            acc[key] = data[key];
            }
            return acc;
        }, {});
        UserB = Object.keys(data).reduce((acc, key) => {
            if (key === 'BUR' || key === 'PB' || key === 'VB' || key === 'BROOM' || key === 'BNAME' || key === 'BSPKR' || key === 'BQFILE' || key === 'BQNAME' || key === 'BQTYPE' || key === 'BQMOD' || key === 'BTACT') {
            acc[key] = data[key];
            }
            return acc;
        }, {});
        Powerstatus = Object.keys(data).reduce((acc, key) => {
            if (key === 'PWR') {
            acc[key] = data[key];
            }
            return acc;
        }, {});
        Levels = Object.keys(data).reduce((acc, key) => {
            if (key === 'L1' || key === 'L2' || key === 'L3' || key === 'L4' || key === 'L5' || key === 'L6' || key === 'L7' || key === 'L8' || key === 'L9' || key === 'L10' || key === 'L11' || key === 'L12' || key === 'L13' || key === 'L14' || key === 'L15' || key === 'L16' || key === 'L17' || key === 'L18' || key === 'L19' || key === 'L20' || key === 'L21' || key === 'L22' || key === 'L23' || key === 'L24' || key === 'AHL' || key === 'AHR' || key === 'ATL' || key === 'ATR' || key === 'BHL' || key === 'BHR' || key === 'BTL' || key === 'BTR') {
            acc[key] = data[key];
            }
            return acc;
        }, {});
        Assignments = Object.keys(data).reduce((acc, key) => {
            if (key.match(/^ACH\d{1,2}$/) || key.match(/^BCH\d{1,2}$/)) {
                acc[key] = data[key];
            }
            return acc;
        }, {});
    
        if (Object.keys(channels).length > 0) {
            updateChannelStates(channels); // Update the state with the new data
            console.log('Channeldata:', channels);
        }
        if (Object.keys(UserA).length > 0) {
            UserA = data;
            updateUserAData();
            setActiveInputButton(UserA.IN);
            setActivePAButton(UserA.PA);
            console.log('UserA:', UserA);
        }
        if (Object.keys(UserB).length > 0) {
            UserB = data;
            updateUserBData();
            setActivePBButton(UserB.PB);
            console.log('UserB:', UserB);
        }
        if (Object.keys(Powerstatus).length > 0) {
            Powerstatus = data;
            console.log('Powerstatus:', Powerstatus);
            handlePowerStatus();
        }
        if (Object.keys(Levels).length > 0) {
            channelLevels = data;
            // console.log('Levels:', channelLevels);
            handleLevels();
        }
        if (Object.keys(Assignments).length > 0) {
            // Assignments = data;
            
            // console.log('Assignments:', Assignments);
            handleAssignments();
        }


    } catch (e) {
        // Handle raw text responses from A16
        console.log('Received raw text response:', event.data);
        if (respDiv && respContent) {
            respContent.textContent = event.data;
            respDiv.scrollTop = respDiv.scrollHeight;
        }
    }
};

// Function to send a command
function sendCommand(commandType, cmdIndex) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: commandType,
            cmd: cmdIndex
        }));
        console.log('Sent command:', commandType, cmdIndex);
    } else {
        console.log('WebSocket not connected, cannot send command');
    }
}

// Fetch commands and create buttons
fetch('/commands')
    .then(response => response.json())
    .then(data => {
        const buttonContainer = document.getElementById('command-buttons');
        
        // IRIP commands
        data.irip.forEach((cmd, index) => {
            const button = document.createElement('button');
            button.textContent = cmd.description;
            button.onclick = () => sendCommand('IRIP', cmd.number);
            buttonContainer.appendChild(button);
        });

        // Non-IRIP commands
        data.nonIrip.forEach((cmd, index) => {
            const button = document.createElement('button');
            button.textContent = cmd.description;
            button.onclick = () => sendCommand('NON_IRIP', cmd.number);
            buttonContainer.appendChild(button);
        });
    });

// Initialize the speaker grid on page load
document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.grid-item');
    console.log('Found', buttons.length, 'speaker buttons');
    buttons.forEach(button => {
        button.addEventListener('click', function () {
            const speakerId = parseInt(this.id) + 105;
            console.log('Clicked speaker button:', this.id, '-> command:', speakerId);
            sendCommand('NON_IRIP', speakerId);
        });
    });
});

function closeConnection() {
    fetch('/close_connection')
        .then(response => response.text())
        .then(data => {
            document.getElementById('response-content').textContent = data;
        });
}

// Keep-alive function to ensure WebSocket connection stays open
function keepAlive() {
    sendCommand('NON_IRIP', 15); // Send a keep-alive command
}

// Set an interval to send keep-alive messages every 30 seconds
setInterval(keepAlive, 10000);


// Send initial commands to get speaker states
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        sendCommand('NON_IRIP', 15); // Power status
        sendCommand('NON_IRIP', 103); // Request speaker key visibility
        sendCommand('NON_IRIP', 104); // Request active speaker status
    }, 3000);
});