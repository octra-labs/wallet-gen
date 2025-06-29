let currentWallet = null;

function updateStatus(message) {
  const status = document.getElementById("status");
  status.textContent += message + "\n";
  status.scrollTop = status.scrollHeight;
}

async function derivePath() {
  if (!currentWallet) {
    alert("Please generate a wallet first");
    return;
  }

  const networkType = parseInt(document.getElementById("networkType").value);
  const index = parseInt(document.getElementById("derivationIndex").value);

  try {
    const response = await fetch("/derive", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        seed_hex: currentWallet.seed_hex,
        network_type: networkType,
        index: index,
      }),
    });

    const result = await response.json();
    if (result.success) {
      document.getElementById("derivedAddressValue").textContent =
        result.address;
      document.getElementById("derivedPath").textContent = result.path;
      document.getElementById("derivedAddress").style.display = "block";
    } else {
      alert("Derivation failed: " + result.error);
    }
  } catch (error) {
    alert("Error: " + error.message);
  }
}

async function generateWallet() {
  const btn = document.getElementById("generateBtn");
  const status = document.getElementById("status");
  const walletInfo = document.getElementById("walletInfo");

  btn.disabled = true;
  status.textContent = "";
  walletInfo.style.display = "none";

  updateStatus("Starting wallet generation...");

  try {
    const response = await fetch("/generate", {
      method: "POST",
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = JSON.parse(line.substring(6));

          if (data.status) {
            updateStatus(data.status);
          }

          if (data.wallet) {
            currentWallet = data.wallet;
            displayWallet(data.wallet);
          }
        }
      }
    }
  } catch (error) {
    updateStatus("ERROR: " + error.message);
  } finally {
    btn.disabled = false;
  }
}

function displayWallet(wallet) {
  document.getElementById("mnemonic").textContent = wallet.mnemonic.join(" ");
  document.getElementById("privateKeyRaw").textContent = wallet.private_key_hex;
  document.getElementById("privateKeyB64").textContent = wallet.private_key_b64;
  document.getElementById("publicKeyRaw").textContent = wallet.public_key_hex;
  document.getElementById("publicKeyB64").textContent = wallet.public_key_b64;
  document.getElementById("address").textContent = wallet.address;
  document.getElementById("entropy").textContent = wallet.entropy_hex;
  document.getElementById("seed").textContent =
    wallet.seed_hex.substring(0, 64) + "...";
  document.getElementById("masterChain").textContent = wallet.master_chain_hex;
  document.getElementById("testMessage").textContent = wallet.test_message;
  document.getElementById("testSignature").textContent = wallet.test_signature;
  document.getElementById("signatureValid").textContent = wallet.signature_valid
    ? "VALID"
    : "INVALID";

  document.getElementById("walletInfo").style.display = "block";

  // Auto-save wallet
  saveWallet();
}

async function saveWallet() {
  if (!currentWallet) return;

  try {
    const response = await fetch("/save", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(currentWallet),
    });

    if (response.ok) {
      const result = await response.json();

      updateStatus("Wallet saved to: " + result.filename);

      document.getElementById("savedFilename").textContent = result.filename;
      document.getElementById("saveInfo").style.display = "flex";
    } else {
      updateStatus("ERROR: Failed to save wallet");
    }
  } catch (error) {
    updateStatus("ERROR: " + error.message);
  }
}
