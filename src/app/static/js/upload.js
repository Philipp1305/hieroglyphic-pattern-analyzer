(function () {
    const initUploadForm = () => {
        const form = document.getElementById('papyrusUploadForm');
        if (!form) {
            return;
        }

        const textInput = document.getElementById('papyrus-name');
        const fileInputs = Array.from(form.querySelectorAll('input[type="file"]'));
        const submitButton = form.querySelector('[data-upload-submit]');
        const resetButtons = Array.from(form.querySelectorAll('[data-file-reset]'));

        const setFileLabel = (input) => {
            const target = form.querySelector(`[data-file-label="${input.name}"]`);
            const resetButton = form.querySelector(`[data-file-reset="${input.name}"]`);
            const hasFile = input.files && input.files.length;
            if (target) {
                target.textContent = hasFile ? input.files[0].name : 'No file chosen';
            }
            if (resetButton) {
                if (hasFile) {
                    resetButton.classList.remove('opacity-0', 'pointer-events-none');
                } else {
                    resetButton.classList.add('opacity-0', 'pointer-events-none');
                }
            }
        };

        const canSubmit = () => {
            const hasName = textInput && textInput.value.trim().length > 0;
            const hasFiles = fileInputs.every((input) => input.files && input.files.length);
            return hasName && hasFiles;
        };

        const updateSubmitState = () => {
            if (submitButton) {
                submitButton.disabled = !canSubmit();
            }
        };

        const resetFile = (input) => {
            input.value = '';
            setFileLabel(input);
            updateSubmitState();
        };

        const resetAllFiles = () => {
            fileInputs.forEach((input) => {
                input.value = '';
                setFileLabel(input);
            });
            updateSubmitState();
        };

        fileInputs.forEach((input) => {
            input.addEventListener('change', () => {
                setFileLabel(input);
                updateSubmitState();
            });
        });

        resetButtons.forEach((button) => {
            const targetName = button.getAttribute('data-file-reset');
            button.addEventListener('click', (event) => {
                event.preventDefault();
                const targetInput = fileInputs.find((input) => input.name === targetName);
                if (targetInput) {
                    resetFile(targetInput);
                }
            });
        });

        if (textInput) {
            textInput.addEventListener('input', updateSubmitState);
        }

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            if (!canSubmit()) {
                return;
            }

            const formData = new FormData(form);
            const fileSummary = fileInputs
                .map((input) => `${input.name}: ${input.files[0].name}`)
                .join('\n');

            // Placeholder behaviour for frontend-only validation.
            alert(`Ready to upload:\nPapyrus: ${formData.get('papyrus_name')}\n${fileSummary}`);
        });

        form.reset();
        resetAllFiles();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUploadForm);
    } else {
        initUploadForm();
    }
})();
