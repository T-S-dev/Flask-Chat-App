const textarea = document.getElementById("input-message");
textarea.addEventListener("input", autoResizeTextArea, false);

const messages = document.getElementById("messages");
const inputArea = document.getElementById("input-message");

function autoResizeTextArea() {
  const style = window.getComputedStyle(textarea);
  const paddingTop = parseInt(style.getPropertyValue("padding-top"));
  const paddingBottom = parseInt(style.getPropertyValue("padding-bottom"));
  const lineHeight = parseInt(style.getPropertyValue("line-height"));

  const maxLines = 5;
  const maxHeight = (maxLines - 1) * lineHeight + paddingTop + paddingBottom;

  this.style.height = "auto";
  this.style.overflowY = "hidden";
  this.style.height = this.scrollHeight + "px";
  if (this.scrollHeight > maxHeight) {
    this.style.overflowY = "scroll";
    this.style.height = maxHeight + paddingTop + "px";
  }
  this.scrollTop = this.scrollHeight;
  messages.scrollTop = messages.scrollHeight;
}

function openMembersList() {
  document.getElementById("members-section").style.width = "250px";
}

function closeMembersList() {
  document.getElementById("members-section").style.width = "0";
}

function sanitizeString(str) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  const reg = /[&<>"']/gi;
  return str.replace(reg, (match) => map[match]);
}

const socket = io();

const convertUtcToLocal = (utcDateTimeString) => {
  // Parse the UTC datetime string
  const utcDateTime = new Date(utcDateTimeString);

  // Manually create a UTC Date object
  const utcDate = new Date(
    utcDateTime.getUTCFullYear(),
    utcDateTime.getUTCMonth(),
    utcDateTime.getUTCDate(),
    utcDateTime.getUTCHours(),
    utcDateTime.getUTCMinutes(),
    utcDateTime.getUTCSeconds(),
    utcDateTime.getUTCMilliseconds()
  );

  // Use toLocaleString to format the date in the user's local timezone
  const formattedDateTime = utcDate.toLocaleString(undefined, {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    hour12: false, // Use 24-hour format
  });

  return formattedDateTime;
};

const createMessage = (name, msg, timestamp, type) => {
  const nameTag = type === "outgoing" ? "" : `<strong>${name}: </strong>`;

  timestamp = convertUtcToLocal(timestamp);

  const message = `
    <div class="message ${type}">
      <span>
        ${nameTag}
        ${msg}
      </span>
      <span class="muted">${timestamp}</span>
    </div>
  `;
  messages.innerHTML += message;
  messages.scrollTop = messages.scrollHeight;
};

const addMember = (name, id) => {
  // Create a new span element for the new member
  const newMember = document.createElement("span");
  newMember.className = "member";
  newMember.textContent = name;

  // Add the new member to the members section
  document.getElementById("members-section").appendChild(newMember);
  localStorage.setItem("userId", id);
};

const removeMember = (name) => {
  // Find the span element for the member who left
  const members = document.getElementsByClassName("member");
  for (let i = 0; i < members.length; i++) {
    if (members[i].textContent === name) {
      // Remove the member from the members section
      members[i].parentNode.removeChild(members[i]);
      break;
    }
  }
};

socket.on("userConnected", (data) => {
  createMessage(data.name, data.message, data.timestamp, "user-connected");
  addMember(data.name, data.id);
});

socket.on("userDisconnected", (data) => {
  createMessage(data.name, data.message, data.timestamp, "user-disconnected");
  removeMember(data.name);
});

socket.on("messageReceived", (data) => {
  createMessage(data.name, data.message, data.timestamp, "incoming");
});

const sendMessage = () => {
  const message = sanitizeString(inputArea.value).trim();
  // Current date time is only used on client side to show when the message was sent
  // Server side date time is used to store the message in the database and send it to other users
  const currentDateTimeUtc = Date.UTC(
    new Date().getUTCFullYear(),
    new Date().getUTCMonth(),
    new Date().getUTCDate(),
    new Date().getUTCHours(),
    new Date().getUTCMinutes(),
    new Date().getUTCSeconds(),
    new Date().getUTCMilliseconds()
  );
  const name = localStorage.getItem("name");
  if (message === "") return;
  socket.emit("messageSent", {
    message: message,
  });
  createMessage(name, message, currentDateTimeUtc, "outgoing");
  inputArea.value = "";
  // Resize textarea to original size
  textarea.style.height = "auto";
};
