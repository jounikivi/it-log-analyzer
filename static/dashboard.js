(function () {
  const form = document.getElementById("analysis-form");
  const sampleButton = document.getElementById("sample-button");
  const uploadField = document.getElementById("upload-field");
  const pathField = document.getElementById("path-field");
  const csvTextField = document.getElementById("csv-text-field");
  const sourceNameField = document.getElementById("source-name-field");
  const modeField = document.getElementById("mode-field");

  if (!form) {
    return;
  }

  sampleButton?.addEventListener("click", function () {
    modeField.value = "sample";
    csvTextField.value = "";
    sourceNameField.value = "";
    if (uploadField) {
      uploadField.value = "";
    }
    if (pathField) {
      pathField.value = "";
    }
    form.submit();
  });

  form.addEventListener("submit", async function (event) {
    modeField.value = "analyze";

    const selectedFile = uploadField?.files?.[0];
    if (!selectedFile) {
      csvTextField.value = "";
      sourceNameField.value = "";
      return;
    }

    event.preventDefault();

    try {
      const csvText = await selectedFile.text();
      csvTextField.value = csvText;
      sourceNameField.value = selectedFile.name;
      if (pathField) {
        pathField.value = "";
      }
      form.submit();
    } catch (error) {
      window.alert("Tiedoston lukeminen selaimessa ei onnistunut.");
    }
  });
})();
