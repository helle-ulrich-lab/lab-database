function ShowLoading(e) {
    var div = document.createElement('div');
    var img = document.createElement('img');
    img.src = '/static/admin/img/helle.gif'; //'/static/admin/img/spinner.svg';
    div.innerHTML = "<br>Wart' mal 'n Moment! ...<br>";
    div.style.cssText = 'margin: 0; height: 15vw; width:15vw; position: absolute; \
     top: 50%; left: 50%; z-index: 5000; transform: translate(-50%, -50%); \
     box-shadow: 0 0 0 100vmax rgba(0,0,0,.3); background-color: white; \
     border: 3px solid #417690; font-family: "Roboto"; text-align: center;';
    img.style.cssText = '-webkit-animation:spin 1.5s linear infinite; \
     -moz-animation:spin 1.5s linear infinite; animation:spin 1.5s linear infinite;';
    div.appendChild(img);
    document.body.appendChild(div);
    return true;
}