function sendMessage() {
  let userInput = document.getElementById("userInput").value;
  let chatBox = document.getElementById("chat-box");

  chatBox.innerHTML += `<div class='user-msg'>🍽️ You: ${userInput}</div>`;
  document.getElementById("userInput").value = "";

  fetch("/get", {
    method: "POST",
    body: new URLSearchParams({ msg: userInput }),
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  })
    .then(res => res.json())
    .then(data => {
      chatBox.innerHTML += `<div class='bot-msg'>🤖 Bot: ${data.response}</div>`;
      chatBox.scrollTop = chatBox.scrollHeight;
    });
}
const response = await fetch("/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message }),
});
