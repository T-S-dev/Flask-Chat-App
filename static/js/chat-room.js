const textarea = document.getElementById("input-message");
textarea.addEventListener("input", autoResizeTextArea, false);

const messages = document.getElementById("messages");
const inputArea = document.getElementById("input-message");

function autoResizeTextArea() {
  var style = window.getComputedStyle(textarea);
  var paddingTop = parseInt(style.getPropertyValue("padding-top"));
  var paddingBottom = parseInt(style.getPropertyValue("padding-bottom"));
  var lineHeight = parseInt(style.getPropertyValue("line-height"));

  var maxLines = 5;
  var maxHeight = (maxLines - 1) * lineHeight + paddingTop + paddingBottom;

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

var socket = io();

const createMessage = (name, msg, dateTime, type) => {
  const nameTag = type === "outgoing" ? "" : `<strong>${name}: </strong>`;

  const message = `
    <div class="message ${type}">
      <span>
        ${nameTag}
        ${msg}
      </span>
      <span class="muted">${dateTime}</span>
    </div>
  `;
  messages.innerHTML += message;
  messages.scrollTop = messages.scrollHeight;
};

const addMember = (name) => {
  // Create a new span element for the new member
  var newMember = document.createElement("span");
  newMember.className = "member";
  newMember.textContent = name;

  // Add the new member to the members section
  document.getElementById("members-section").appendChild(newMember);
};

const removeMember = (name) => {
  // Find the span element for the member who left
  var members = document.getElementsByClassName("member");
  for (var i = 0; i < members.length; i++) {
    if (members[i].textContent === name) {
      // Remove the member from the members section
      members[i].parentNode.removeChild(members[i]);
      break;
    }
  }
};

socket.on("userConnected", (data) => {
  createMessage(data.name, data.message, data.dateTime, "user-connected");
  addMember(data.name);
});

socket.on("userDisconnected", (data) => {
  createMessage(data.name, data.message, data.dateTime, "user-disconnected");
  removeMember(data.name);
});

socket.on("messageReceived", (data) => {
  createMessage(data.name, data.message, data.dateTime, "incoming");
});

const sendMessage = () => {
  const message = sanitizeString(inputArea.value).trim();
  const currentDateTime = new Date().toLocaleString();
  const name = localStorage.getItem("name");
  if (message === "") return;
  socket.emit("messageSent", {
    message: message,
    dateTime: currentDateTime,
  });
  createMessage(name, message, currentDateTime, "outgoing");
  inputArea.value = "";
  // Resize textarea to original size
  textarea.style.height = "auto";
};
