$(function () {
    $(".js-upload-packages").click(function () {
        $("#fileupload").click();
    });

    function get_layer_template(layers) {
        var items = []
        layers.forEach(layer => {
            const t = '<li class="list-group-item ">' +
                '<div class="layer-item flex-element flex-space-between equal-area text-center flex-center">' +
                '<span class="text-wrap equal-area text-left">Layer Name: ' + layer.name + '</span>' +
                '<span class="equal-area">Type:' + layer.type + '</span>' +
                '<span class="equal-area">Feature Count:' + layer.feature_count + '</span>' +
                '<button class="btn btn-primary glayer-actions" onclick="showPublishModal(' + "'" + layer.urls.publish_url + "'," + "'" + layer.expected_publish_name + "'" + ')">Publish</button>' +
                '<button class="btn btn-primary glayer-actions" onclick="getCompatibleLayres(' + "'" + layer.urls.compatible_layers + "'" + ')">Update</button>' +
                '</div>' +
                '</li>'
            items.push(t)
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
                const t = '<div id="package-' + uploaded.id + '" class="container panel-group">' +
                    '<div class="panel panel-primary">' +
                    '<div class="panel-heading">' +
                    '<div class="layer-item flex-element flex-space-between equal-area text-center flex-center">' +
                    '<span class="text-wrap equal-area text-left">' + uploaded.name + ' </span>' +
                    '<span class="equal-area">uploaded:' + uploaded.uploaded_at + '</span>' +
                    '<a href="' + uploaded.download_url + '" class="btn btn-success equal-area glayer-actions">Download</a>' +
                    '<button onclick="deletePackage(' + "'" + uploaded.delete_url + "'," + uploaded.id + ')" class="btn btn-danger equal-area glayer-actions">Delete</button>' +
                    '</div>' +
                    '</div>' +
                    '<div class="panel-body">' +
                    '<ul class="list-group">' +
                    get_layer_template(uploaded.layers) +
                    '</ul>' +
                    '</div>' +
                    '</div>';
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
            Accept: "application/json; charset=utf-8",
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
const deletePackage = function (deleteURL, id) {
    $("#modal-publishing").modal("show");
    $.ajax({
        url: deleteURL,
        type: 'GET',
        headers: {
            'X-CSRFToken': getCRSFToken(),
            Accept: "application/json; charset=utf-8",
        },
        contentType: 'application/json; charset=utf-8',
        success: function (result) {
            if (result.status === "success") {
                if ($('#package-' + id).length) {
                    $('#package-' + id).remove()
                }
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
const compareSchema = function (compareURL) {
    $("#modal-publishing").modal("show");
    $.ajax({
        url: compareURL,
        type: 'GET',
        headers: {
            'X-CSRFToken': getCRSFToken(),
            Accept: "application/json; charset=utf-8",
        },
        contentType: 'application/json; charset=utf-8',
        success: function (result) {
            $("#modal-publishing").modal("hide");
            setTimeout(function () {
                if (result.status === "success" && result.compitable) {
                    alert("the same schema")
                } else {
                    alert("not the same schema")
                }
            }, 500)
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

function get_compatible_template(layers) {
    var items = []
    layers.forEach(layer => {
        const t = '<div class="flex-element flex-space-between equal-area text-center flex-center">' +
            '<span class="text-wrap equal-area text-left">' + layer.name + '</span>' +
            '<button onclick="reloadLayer(' + "'" + layer.urls.reload_url + "')" + '" class="btn btn-primary glayer-actions">reload</button>' +
            '</div>'
        items.push(t)
    })
    if (items.length == 0) {
        items.push("<h4>cannot find layers with the same schema</h4>")
    }
    return items.join('\n')
}
const reloadLayer = function (reloadURL) {
    $("#modal-compatible-layers").modal("hide");
    $("#modal-publishing").modal("show");
    $.ajax({
        url: reloadURL,
        type: 'GET',
        headers: {
            'X-CSRFToken': getCRSFToken(),
            Accept: "application/json; charset=utf-8",
        },
        contentType: 'application/json; charset=utf-8',
        success: function (result) {
            $("#modal-publishing").modal("hide");
            setTimeout(function () {
                alert(result.message)
            }, 500)
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
            $("#modal-compatible-layers").modal("hide");

        }
    });
}
const getCompatibleLayres = function (LayersURL) {
    $(".compatible-layers").empty()
    $(".compatible-layers").prepend('<div class="progress">' +
        '<div class="progress-bar progress-bar-striped active" role="progressbar" style="width: 100%;">Processing</div>' +
        '</div>');
    $("#modal-compatible-layers").modal("show");
    $.ajax({
        url: LayersURL,
        type: 'GET',
        headers: {
            'X-CSRFToken': getCRSFToken(),
            Accept: "application/json; charset=utf-8",
        },
        contentType: 'application/json; charset=utf-8',
        success: function (result) {
            setTimeout(function () {
                if (result.status === "success") {
                    $(".compatible-layers").empty()
                    $(".compatible-layers").prepend(get_compatible_template(result.layers))
                } else {
                    alert(result.message)
                }
            }, 500)
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
            $("#modal-compatible-layers").modal("hide");

        }
    });
}

function convertToSlug(Text) {
    return Text
        .toLowerCase()
        .replace(/ /g, '_')
        .replace(/[^\w-]+/g, '');
}
const showPublishModal = function (publishURL, expectedName) {
    $("#modal-prepublish").modal("show");
    $('#publishname').val(expectedName)
    $("#publishname").on("change paste keyup", function () {
        var slugified = convertToSlug($(this).val())
        $('#publishname').val(slugified)
    });
    $("#publish-btn").on("click", function () {
        const layername = $('#publishname').val()
        if (layername) {
            $.ajax({
                url: '/api/layers/?alternate__icontains=' + layername,
                type: 'GET',
                headers: {
                    'X-CSRFToken': getCRSFToken(),
                    Accept: "application/json; charset=utf-8",
                },
                contentType: 'application/json; charset=utf-8',
                success: function (result) {
                    if (result.objects.length > 0) {
                        alert("Layer already exists. please choose another name")
                    } else {
                        $("#modal-prepublish").modal("hide");
                        publishLayer(publishURL + "/" + layername)
                    }
                },
                error: function (xhr, status, error) {
                    try {
                        result = JSON.parse(xhr.responseText)
                        alert(result.message)
                    } catch (err) {
                        alert(xhr.responseText)
                    }
                }
            });
        }
    });
}
const downloadModal = function () {
    var selectedLayers = []
    $("#download-layers").attr("disabled", true)
    $('#layer-selector').multiSelect({
        selectableHeader: "<input type='text' class='search-input form-control' autocomplete='off' placeholder='search layers'>",
        selectionHeader: "<input type='text' class='search-input form-control' autocomplete='off' placeholder='search selected'>",
        selectionFooter: "<div class='custom-header'>Selected Layers</div>",
        selectableFooter: "<div class='custom-header'>All Layers</div>",
        afterInit: function (ms) {
            var that = this,
                $selectableSearch = that.$selectableUl.prev(),
                $selectionSearch = that.$selectionUl.prev(),
                selectableSearchString = '#' + that.$container.attr('id') + ' .ms-elem-selectable:not(.ms-selected)',
                selectionSearchString = '#' + that.$container.attr('id') + ' .ms-elem-selection.ms-selected';

            that.qs1 = $selectableSearch.quicksearch(selectableSearchString)
                .on('keydown', function (e) {
                    if (e.which === 40) {
                        that.$selectableUl.focus();
                        return false;
                    }
                });

            that.qs2 = $selectionSearch.quicksearch(selectionSearchString)
                .on('keydown', function (e) {
                    if (e.which == 40) {
                        that.$selectionUl.focus();
                        return false;
                    }
                });
        },
        afterSelect: function (values) {
            this.qs1.cache();
            this.qs2.cache();
            selectedLayers.push(values)
            if (selectedLayers.length > 0) {
                $("#download-layers").removeAttr("disabled");
            } else {
                $("#download-layers").attr("disabled", true)
            }
        },
        afterDeselect: function (values) {
            this.qs1.cache();
            this.qs2.cache();
            selectedLayers.splice(selectedLayers.indexOf(values))
            if (selectedLayers.length > 0) {
                $("#download-layers").removeAttr("disabled");
            } else {
                $("#download-layers").attr("disabled", true)
            }
        }
    });
    $("#download-layers").on("click", function () {
        var win = window.open(
            urls.downloadLayers + "?layers=" + selectedLayers.join(','),
            '_blank');
        win.focus();
    })
    $("#modal-downloader").modal("show");
}