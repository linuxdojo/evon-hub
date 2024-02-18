document.addEventListener('DOMContentLoaded', function () {
  var inputField = document.getElementById('id_fqdn');
  if (inputField && inputField.getAttribute('account_domain')) {
		var accountDomain = inputField.getAttribute('account_domain');
		var newElement = document.createElement('span');
		newElement.textContent = '.' + accountDomain;
		newElement.style.fontFamily = 'monospace';
		newElement.style.marginLeft = '5px';
		inputField.parentNode.insertBefore(newElement, inputField.nextSibling);
  }
});

function generateRandomString(length) {
  var result = '';
  var characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  var charactersLength = characters.length;
  for (var i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
  }
  return result;
}

// Function to set the random string to the input field
function setRandomPasskey() {
  document.getElementById('id_passkey').value = generateRandomString(32);
}

// Function to create and add the generate link next to the input field
function addGenerateLink() {
	var generateLink = document.createElement('a');
	generateLink.href = '#';
	generateLink.innerText = ' Generate new random passkey ';
	generateLink.onclick = function(event) {
		event.preventDefault(); // Prevent the link from navigating.
		setRandomPasskey();
	};
	
	var passkeyField = document.getElementById('id_passkey');
	// Insert the generate link after the input field
	passkeyField.parentNode.insertBefore(generateLink, passkeyField.nextSibling);
}

// Call the function to add the generate link when the window loads
window.onload = addGenerateLink;
