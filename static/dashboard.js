(function () {
  const uploadField = document.getElementById("upload-field");
  const uploadHelp = document.getElementById("upload-help");

  if (!uploadField || !uploadHelp) {
    return;
  }

  const defaultHelpText = uploadHelp.dataset.defaultText || uploadHelp.textContent || "";

  uploadField.addEventListener("change", function () {
    const selectedFile = uploadField.files?.[0];
    if (!selectedFile) {
      uploadHelp.textContent = defaultHelpText;
      return;
    }

    const sizeInKb = (selectedFile.size / 1024).toFixed(1);
    uploadHelp.textContent = "Valittu tiedosto: " + selectedFile.name + " (" + sizeInKb + " KB)";
  });
})();
