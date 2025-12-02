$(document).ready(function() {
    const dropZone = $('#drop-zone');
    const fileInput = $('#file-input');
    const fileListEl = $('#file-list');
    const filesSection = $('#files-section');
    const syncAlert = $('#sync-alert');
    const trainBtn = $('#train-btn');
    const progressContainer = $('#progress-container');
    const progressBar = $('#progress-bar');
    const progressLabel = $('#progress-label');
    const progressPercent = $('#progress-percent');
    const impactCurrent = $('#impact-current');
    const impactEstimated = $('#impact-estimated');
    
    // Initialization
    fetchFiles();
    fetchInfo();
    checkTrainingStatus();
    updateHeaderStatus();

    // --- Drag & Drop Logic ---
    // jQuery handles events slightly differently, passing a jQuery event object. 
    // We need originalEvent for dataTransfer.
    
    dropZone.on('dragenter dragover dragleave drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
    });

    dropZone.on('dragenter dragover', function() {
        dropZone.addClass('drag-over');
    });

    dropZone.on('dragleave drop', function() {
        dropZone.removeClass('drag-over');
    });

    dropZone.on('drop', function(e) {
        const files = e.originalEvent.dataTransfer.files;
        handleFiles(files);
    });

    fileInput.on('change', function(e) {
        const files = e.target.files;
        handleFiles(files);
    });

    function handleFiles(files) {
        const formData = new FormData();
        let validFiles = false;
        
        $.each(files, function(i, file) {
            if (file.type === 'application/pdf') {
                formData.append('files', file);
                validFiles = true;
            }
        });

        if (validFiles) {
            uploadFiles(formData);
        } else {
            alert("Please upload PDF files only.");
        }
    }

    // --- API Calls (jQuery AJAX) ---

    async function updateHeaderStatus() {
        try {
            const data = await $.ajax({ url: '/api/status', type: 'GET' });
            const badge = $('#nav-status-badge');
            const dot = $('#nav-status-dot');
            const text = $('#nav-status-text');

            if(data.last_trained_at) {
                dot.removeClass('bg-slate-300 bg-red-500').addClass('bg-emerald-500');
                badge.addClass('border-emerald-200 bg-emerald-50');
                text.text("Index Active").addClass('text-emerald-700').removeClass('text-slate-500');
                badge.attr('title', `Last updated: ${data.last_trained_at}`);
            } else {
                dot.removeClass('bg-slate-300 bg-emerald-500').addClass('bg-amber-400');
                text.text("Not Indexed");
            }
        } catch(e) {
            $('#nav-status-dot').addClass('bg-red-500');
            $('#nav-status-text').text("Offline");
        }
    }

    async function uploadFiles(formData) {
        // UI indicating upload start
        dropZone.html(`<div class="text-blue-600"><i class="fa-solid fa-circle-notch fa-spin text-2xl"></i><p class="mt-2">Uploading...</p></div>`);
        
        try {
            await $.ajax({
                url: '/upload',
                type: 'POST',
                data: formData,
                processData: false, // Important for FormData
                contentType: false, // Important for FormData
            });
            
            fetchFiles(); 
            fetchInfo();  
        } catch (error) {
            console.error('Error uploading:', error);
            alert("Upload failed.");
        } finally {
            // Reset Dropzone
            setTimeout(() => {
                dropZone.html(`
                    <input type="file" id="file-input" class="hidden" multiple accept="application/pdf">
                    <div class="mb-4"><i class="fa-solid fa-cloud-arrow-up text-4xl text-gray-300"></i></div>
                    <h3 class="text-lg font-semibold text-gray-700 mb-2">Drag & Drop PDFs here</h3>
                    <p class="text-gray-500 text-sm mb-4">or click to browse files</p>
                    <button id="browse-btn" class="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition">Browse Files</button>
                `);
                
                // Re-bind click event to the new button since HTML was replaced
                $('#browse-btn').on('click', function() {
                    $('#file-input').click();
                });
                // Re-bind change event to input
                $('#file-input').on('change', function(e) {
                    handleFiles(e.target.files);
                });
            }, 500);
        }
    }

    async function fetchFiles() {
        try {
            const files = await $.ajax({ url: '/files', type: 'GET' });

            // Update Badge
            $('#file-count-badge').text(`${files.length} files`);
            
            // Update List
            if (files.length > 0) {
                fileListEl.empty();
                trainBtn.prop('disabled', false);
                
                $.each(files, function(index, file) {
                    const li = $(`
                        <li class="p-4 flex items-center justify-between hover:bg-gray-50 transition fade-in">
                            <div class="flex items-center gap-4">
                                <div class="text-red-500 bg-red-50 p-2 rounded">
                                    <i class="fa-regular fa-file-pdf text-xl"></i>
                                </div>
                                <div>
                                    <p class="font-medium text-gray-800 text-sm truncate w-64" title="${file.filename}">${file.filename}</p>
                                    <p class="text-xs text-gray-500">${file.pages} pages • ${file.size}</p>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <a href="/files/view/${file.filename}" target="_blank" class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition" title="Preview">
                                    <i class="fa-regular fa-eye"></i>
                                </a>
                                <button class="delete-btn p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition" data-filename="${file.filename}" title="Remove">
                                    <i class="fa-regular fa-trash-can"></i>
                                </button>
                            </div>
                        </li>
                    `);
                    fileListEl.append(li);
                });

                // Attach click handlers for delete buttons
                $('.delete-btn').on('click', function() {
                    deleteFile($(this).data('filename'));
                });
            } else {
                // filesSection.addClass('hidden');
                trainBtn.prop('disabled', true);
            }

            const estVectors = totalPages * 3; 
        } catch (e) {
            console.error("Error fetching files", e);
        }
    }

    window.deleteFile = async (filename) => {
        if(!confirm(`Remove ${filename}?`)) return;
        try {
            await $.ajax({ url: `/files/${filename}`, type: 'DELETE' });
            fetchFiles();
            fetchInfo();
        } catch (e) {
            alert("Error deleting file");
        }
    };

    async function fetchInfo() {
        try {
            const data = await $.ajax({ url: '/info', type: 'GET' });
            
            $('#info-pdf-count').text(data.pdf_count);
            $('#info-vectors').text(data.vectors_indexed);
            $('#info-last-trained').text(data.last_trained_at || "Never");
            $('#info-model-emb').text(data.embedding_model);
            $('#info-model-llm').text(data.llm_model);
            impactCurrent.text(data.vectors_indexed);

            if (data.pdf_count != parseInt(data.no_of_files_to_train)) {
                syncAlert.removeClass('hidden').addClass('block');
            } else {
                syncAlert.removeClass('block').addClass('hidden');
            }
        } catch (e) {
            console.log("Could not fetch info");
        }
    }

    // --- Training Logic ---
    
    window.scrollToTrain = function() {
        $('html, body').animate({
            scrollTop: $("#train-btn").offset().top - 100
        }, 500);
        // Optional: Highlight the button briefly
        $('#train-btn').addClass('ring-4 ring-blue-300').delay(1000).queue(function(next){
            $(this).removeClass('ring-4 ring-blue-300');
            next();
        });
    };

    trainBtn.on('click', async function() {
        trainBtn.prop('disabled', true);
        try {
            await $.ajax({ url: '/train', type: 'POST' });
            pollTrainingStatus();
        } catch (e) {
            alert("Failed to start training");
            trainBtn.prop('disabled', false);
        }
    });

    async function checkTrainingStatus() {
        try {
            const state = await $.ajax({ url: '/train/status', type: 'GET' });
            if (state.is_training) {
                pollTrainingStatus();
            }
        } catch(e) {}
    }

    function pollTrainingStatus() {
        progressContainer.removeClass('hidden');
        trainBtn.prop('disabled', true);
        trainBtn.html(`<i class="fa-solid fa-circle-notch fa-spin"></i> Processing...`);

        const interval = setInterval(async () => {
            try {
                const state = await $.ajax({ url: '/train/status', type: 'GET' });

                // Update UI
                progressBar.css('width', `${state.progress}%`);
                progressLabel.text(state.stage);
                progressPercent.text(`${state.progress}%`);

                if (!state.is_training) {
                    clearInterval(interval);
                    // Finished
                    setTimeout(() => {
                        progressContainer.addClass('hidden');
                        trainBtn.prop('disabled', false);
                        trainBtn.html(`<i class="fa-solid fa-bolt"></i> Train / Index Documents`);
                        fetchInfo(); 
                        alert(state.message);
                    }, 1000);
                }
            } catch (e) {
                clearInterval(interval);
            }
        }, 1000);
    }
});