function ShowLoading() {
    var div = document.createElement('div');
    var loader = document.createElement('div');
    loader.className = "lds-ring";
    loader.innerHTML = "<div></div><div></div><div></div><div></div>";
    div.innerHTML = "</br>Please wait...</br></br>";
    div.className = 'spinner-loader'
    div.style.cssText = 'margin: 0; height: 10vw; width: 10vw; position: fixed; \
     top: 50%; left: 50%; z-index: 5000; transform: translate(-50% , -50%); \
     -webkit-transform: translate(-50%, -50%); box-shadow: 0 0 0 100vmax rgba(0, 0, 0, .8); \
     background-color: var(--body-bg); border: 3px solid var(--secondary); \
     border-radius: 3px; font-family: "Roboto"; text-align: center;';
    div.appendChild(loader);
    document.body.appendChild(div);
}