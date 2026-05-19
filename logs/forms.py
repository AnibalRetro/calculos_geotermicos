from django import forms


class LASUploadForm(forms.Form):
    las_file = forms.FileField(
        label='Archivo LAS',
        widget=forms.ClearableFileInput(attrs={'accept': '.las'}),
        help_text='Selecciona un archivo con extensión .las',
    )

    def clean_las_file(self):
        uploaded_file = self.cleaned_data['las_file']
        filename = uploaded_file.name.lower()
        if not filename.endswith('.las'):
            raise forms.ValidationError('Solo se permiten archivos con extensión .las')
        return uploaded_file
