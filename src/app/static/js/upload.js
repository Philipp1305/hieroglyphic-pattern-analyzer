document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("papyrusUploadForm");
  if (!form) return;

  const socket = typeof io === "function" ? io() : null;
  const nameInput = document.getElementById("papyrus-name-input");
  const fileInputs = Array.from(form.querySelectorAll('input[type="file"]'));
  const submitButton = form.querySelector("[data-upload-submit]");
  const submitSpinner = submitButton?.querySelector(
    "[data-upload-submit-spinner]",
  );
  const submitIcon = submitButton?.querySelector("[data-upload-submit-icon]");
  const submitText = submitButton?.querySelector("[data-upload-submit-text]");
  const resetButtons = Array.from(form.querySelectorAll("[data-file-reset]"));
  const errorBanner = document.querySelector("[data-upload-error]");
  const errorMessage = document.querySelector("[data-upload-error-message]");
  const defaultSubmitText =
    (submitText && submitText.textContent.trim()) || "Process Papyrus";
  let isUploading = false;

  const showError = (message) => {
    if (!errorBanner) {
      alert(message);
      return;
    }

    if (errorMessage) {
      errorMessage.textContent = message || "Upload failed. Please try again.";
    }

    errorBanner.classList.remove("hidden");
  };

  const clearError = () => {
    if (!errorBanner) {
      return;
    }

    errorBanner.classList.add("hidden");

    if (errorMessage) {
      errorMessage.textContent = "";
    }
  };

  // Hilfsfunktion: Label + "Remove file"-Button aktualisieren
  const setFileLabel = (input) => {
    const target = form.querySelector(`[data-file-label="${input.name}"]`);
    const resetButton = form.querySelector(`[data-file-reset="${input.name}"]`);
    const hasFile = input.files && input.files.length > 0;

    if (target) {
      target.textContent = hasFile ? input.files[0].name : "No file chosen";
    }

    if (resetButton) {
      if (hasFile) {
        resetButton.classList.remove("opacity-0", "pointer-events-none");
      } else {
        resetButton.classList.add("opacity-0", "pointer-events-none");
      }
    }
  };

  // Darf man abschicken?
  const canSubmit = () => {
    const hasName = nameInput && nameInput.value.trim().length > 0;
    const hasFiles = fileInputs.every(
      (input) => input.files && input.files.length > 0,
    );
    return hasName && hasFiles;
  };

  const updateSubmitState = () => {
    if (submitButton) {
      submitButton.disabled = !canSubmit() || isUploading;
    }
  };

  const setLoadingState = (loading) => {
    isUploading = loading;
    if (submitSpinner) {
      submitSpinner.classList.toggle("hidden", !loading);
    }
    if (submitIcon) {
      submitIcon.classList.toggle("hidden", loading);
    }
    if (submitText) {
      submitText.textContent = loading ? "Uploading..." : defaultSubmitText;
    }
    updateSubmitState();
  };

  // Einzelnes File zurücksetzen
  const resetFile = (input) => {
    input.value = "";
    setFileLabel(input);
    updateSubmitState();
  };

  // Alle Files zurücksetzen
  const resetAllFiles = () => {
    fileInputs.forEach((input) => {
      input.value = "";
      setFileLabel(input);
    });
    updateSubmitState();
  };

  // Listener: wenn Datei gewählt wurde
  fileInputs.forEach((input) => {
    input.addEventListener("change", () => {
      setFileLabel(input);
      updateSubmitState();
    });
  });

  // Listener: "Remove file"-Buttons
  resetButtons.forEach((button) => {
    const targetName = button.getAttribute("data-file-reset");
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const targetInput = fileInputs.find((input) => input.name === targetName);
      if (targetInput) {
        resetFile(targetInput);
      }
    });
  });

  // Name-Input überwachen
  if (nameInput) {
    nameInput.addEventListener("input", updateSubmitState);
  }

  const handleUploadResult = (payload) => {
    const isSuccess = payload && payload.status === "success";
    if (isUploading) {
      setLoadingState(false);
    }
    if (isSuccess) {
      clearError();
      window.location.href = `/overview?id=${payload.id}`;
      return;
    }

    const message =
      (payload && payload.message) || "Upload failed. Please try again.";
    showError(message);
  };

  // Submit-Handler
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!canSubmit()) {
      return;
    }

    clearError();
    setLoadingState(true);

    const formData = new FormData(form);

    // fetch POST mit multipart/form-data
    try {
      const response = await fetch("/api/upload_papyrus", {
        method: "POST",
        body: formData,
      });

      let result;
      try {
        result = await response.json();
      } catch (parseError) {
        throw new Error("Unexpected server response.");
      }

      console.log("Upload result:", result);

      if (!response.ok) {
        const message =
          (result && result.message) ||
          `Upload failed with status ${response.status}.`;
        throw new Error(message);
      }

      handleUploadResult(result);
    } catch (error) {
      console.error("Upload failed:", error);
      showError(error.message || "Upload failed. Please try again.");
    } finally {
      setLoadingState(false);
    }
  });

  if (socket) {
    socket.on("s2c:upload_papyrus:response", (data) => {
      console.log("Server response:", data);
      handleUploadResult(data);
    });
  }
  form.reset();
  resetAllFiles();
  updateSubmitState();
});
