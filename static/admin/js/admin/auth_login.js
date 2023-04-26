// Hide/Show local login form

document.addEventListener("DOMContentLoaded", function () {
    var button = document.getElementsByClassName("collapsible")[0];

    button.addEventListener("click", function () {
        this.classList.toggle("active");
        var content = this.nextElementSibling;
        if (content.style.display === "block") {
            content.style.display = "none";
        } else {
            content.style.display = "block";
        }
    });
})