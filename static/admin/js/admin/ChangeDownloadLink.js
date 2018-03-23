$(document).ready(
    function() {
        var page_title = $(document).find("title").text();
        if (page_title.toLowerCase().indexOf("plasmid") >= 0 && page_title.startsWith("Change")) {
            var download_element = $('.form-row.field-plasmid_map').find("a");
            var link_address = download_element.attr("href");
            if (link_address) {
                var link_address_split = link_address.split("/")[3].split("_");
                var plasmid_name = $(".form-row.field-name").find(".readonly").text()
                if (!plasmid_name){
                    plasmid_name = $('input[name=name]').val()
                }                
                var file_name = link_address_split[0] + " - " + plasmid_name + "." + link_address_split[2].split(".")[1];
                download_element.attr("download", file_name);
                download_element.text("Download");
            }
        }
        if (page_title.startsWith("Change antibody")) {
            var download_element = $('.form-row.field-info_sheet').find("a");
            var link_address = download_element.attr("href");
            if (link_address) {
                var link_address_split = link_address.split("/")[3].split("_")[2].split(".");
                var antibody_name = $(".form-row.field-name").find(".readonly").text()
                if (!antibody_name){
                    antibody_name = $('input[name=name]').val()
                }                
                var file_name = "aHU" + link_address_split[0] + " - " + antibody_name + "." + link_address_split[1];
                download_element.attr("download", file_name);
                download_element.text("Download");
            }
        }
    });