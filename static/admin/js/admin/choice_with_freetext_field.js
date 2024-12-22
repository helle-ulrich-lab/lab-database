$(window).on("load", function () {
  for (fieldProp of freeTextFieldIds) {
    // Toggle visibility of free text field for Lab Identifier
    // field, based on value of choice field
    let fieldName = fieldProp[0];
    let required = fieldProp[1];

    if (required) {
      $(`.field-${fieldName}`).find("label")[0].classList.add("required"); // Show Lab Identifier label as required
    }
    let labIdentifierFreeChoiceField = $(`#id_${fieldName}_1`);
    $(`#id_${fieldName}_0`)[0].value === ""
      ? labIdentifierFreeChoiceField.show()
      : labIdentifierFreeChoiceField.hide();
  }
});

$(document).ready(function () {
  // Toggle visibility of free text field for Lab Identifier
  // field, based on value of choice field upon change
  for (fieldProp of freeTextFieldIds) {
    let fieldName = fieldProp[0];
    $(`#id_${fieldName}_0`).on("change", function () {
      let freeChoiceField = $(`#id_${fieldName}_1`);
      if (this.value === "") {
        freeChoiceField.show();
      } else {
        freeChoiceField[0].value = "";
        freeChoiceField.hide();
      }
    });
  }
});
