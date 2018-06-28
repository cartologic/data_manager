$(function () {
    $(".js-upload-packages").click(function () {
        $("#fileupload").click();
    });

    function get_layer_template(layers) {
        var items = []
        layers.forEach(layer => {
            items.push('<li  style="display: flex;" class="list-group-item"><span style="flex-grow: 1">' + layer.name + '</span><button onclick="publishLayer(' + "'" + layer.urls.publish_url + "'" + ')" class="btn btn-primary">publish</a></li>')
        })
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
                if ($('#no-uploads').length) {
                    $('#no-uploads').remove()
                }
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
        },
        error: function (e, data) {
            if (!e.status < 400) {
                alert(e.statusText)
            }
        }
    }).on("fileuploadprocessfail", function (e, data) {
        var file = data.files[data.index];
        alert(file.error);
    });

})

function getCRSFToken() {
    let csrfToken, csrfMatch = document.cookie.match(/csrftoken=(\w+)/)
    if (csrfMatch && csrfMatch.length > 0) {
        csrfToken = csrfMatch[1]
    }
    return csrfToken
}
const publishLayer = function (publishURL) {
    $("#modal-publishing").modal("show");
    $.ajax({
        url: publishURL,
        type: 'GET',
        headers: {
            'X-CSRFToken': getCRSFToken(),
            Accept: "text/plain; charset=utf-8",
        },
        contentType: 'application/json; charset=utf-8',
        success: function (result) {
            if (result.status === "success") {
                window.location.href = result.layer_url
            }
            $("#modal-publishing").modal("hide");
        },
        error: function (xhr, status, error) {
            try {
                result = JSON.parse(xhr.responseText)
                if (result.status === 'failed') {
                    alert(result.message)
                }
            } catch (err) {
                alert(xhr.responseText)
            }
            $("#modal-publishing").modal("hide");

        }
    });
}