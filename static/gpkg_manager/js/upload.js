$(function () {
    $(".js-upload-packages").click(function () {
        $("#fileupload").click();
    });

    function get_layer_template(layers) {
        var items = []
        layers.forEach(layer => {
            items.push('<li  style="display: flex;" class="list-group-item"><span style="flex-grow: 1">' + layer.name + '</span><a href="' + layer.urls.publish_url + '">publish</a></li>')
        })
        console.log(items)
        return items.join('\n')
    }

    $("#fileupload").fileupload({
        dataType: 'json',
        sequentialUploads: true,
        /* 1. SEND THE FILES ONE BY ONE */
        start: function (e) { /* 2. WHEN THE UPLOADING PROCESS STARTS, SHOW THE MODAL */
            $("#modal-progress").modal("show");
        },
        stop: function (e) { /* 3. WHEN THE UPLOADING PROCESS FINALIZE, HIDE THE MODAL */
            $("#modal-progress").modal("hide");
        },
        progressall: function (e, data) { /* 4. UPDATE THE PROGRESS BAR */
            var progress = parseInt(data.loaded / data.total * 100, 10);
            var strProgress = progress + "%";
            $(".progress-bar").css({
                "width": strProgress
            });
            $(".progress-bar").text(strProgress);
        },
        done: function (e, data) { /* 3. PROCESS THE RESPONSE FROM THE SERVER */
            if (data.result.is_valid) {
                const uploaded = data.result
                const t = '<div class="panel-group">' +
                    '<div class="panel panel-primary">' +
                    '<div style="display: flex;justify-content: space-between;" class="panel-heading"> <span>' + uploaded.name + '</span> <span>uploaded: ' + uploaded.uploaded_at + '</span> </div>' +
                    '<div class="panel-body">' +
                    '<ul class="list-group">' + get_layer_template(uploaded.layers) +
                    '</ul>' +
                    '</div>' +
                    '</div>' +
                    '</div>'
                $("#uploaded_list").prepend(t)

            } else {
                alert('invalid file')
            }
        }
    });

});