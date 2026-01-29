# CodeVault License Activation Dialog
# Modern WinForms dialog with dark theme styling
# Usage: powershell -ExecutionPolicy Bypass -File license_dialog.ps1

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Create main form
$form = New-Object System.Windows.Forms.Form
$form.Text = "License Activation Required"
$form.Size = New-Object System.Drawing.Size(480, 280)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(17, 24, 39)
$form.ForeColor = [System.Drawing.Color]::FromArgb(229, 231, 235)
$form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

# Icon panel (left side gradient effect simulation)
$iconPanel = New-Object System.Windows.Forms.Panel
$iconPanel.Size = New-Object System.Drawing.Size(80, 280)
$iconPanel.Location = New-Object System.Drawing.Point(0, 0)
$iconPanel.BackColor = [System.Drawing.Color]::FromArgb(99, 102, 241)
$form.Controls.Add($iconPanel)

# Lock icon label
$iconLabel = New-Object System.Windows.Forms.Label
$iconLabel.Text = [char]0x1F512  # Lock emoji
$iconLabel.Font = New-Object System.Drawing.Font("Segoe UI Emoji", 28)
$iconLabel.Size = New-Object System.Drawing.Size(80, 60)
$iconLabel.Location = New-Object System.Drawing.Point(0, 90)
$iconLabel.TextAlign = 'MiddleCenter'
$iconLabel.ForeColor = [System.Drawing.Color]::White
$iconPanel.Controls.Add($iconLabel)

# Title label
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = "License Key Required"
$titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$titleLabel.Size = New-Object System.Drawing.Size(360, 35)
$titleLabel.Location = New-Object System.Drawing.Point(100, 25)
$titleLabel.ForeColor = [System.Drawing.Color]::FromArgb(243, 244, 246)
$form.Controls.Add($titleLabel)

# Description label
$descLabel = New-Object System.Windows.Forms.Label
$descLabel.Text = "Please enter your license key to activate this application."
$descLabel.Size = New-Object System.Drawing.Size(360, 25)
$descLabel.Location = New-Object System.Drawing.Point(100, 60)
$descLabel.ForeColor = [System.Drawing.Color]::FromArgb(156, 163, 175)
$form.Controls.Add($descLabel)

# License key input
$inputBox = New-Object System.Windows.Forms.TextBox
$inputBox.Size = New-Object System.Drawing.Size(340, 35)
$inputBox.Location = New-Object System.Drawing.Point(100, 100)
$inputBox.Font = New-Object System.Drawing.Font("Consolas", 12)
$inputBox.BackColor = [System.Drawing.Color]::FromArgb(31, 41, 55)
$inputBox.ForeColor = [System.Drawing.Color]::FromArgb(229, 231, 235)
$inputBox.BorderStyle = 'FixedSingle'
$form.Controls.Add($inputBox)

# Hint label
$hintLabel = New-Object System.Windows.Forms.Label
$hintLabel.Text = "Format: LIC-XXXX-XXXX-XXXX"
$hintLabel.Size = New-Object System.Drawing.Size(340, 20)
$hintLabel.Location = New-Object System.Drawing.Point(100, 138)
$hintLabel.ForeColor = [System.Drawing.Color]::FromArgb(107, 114, 128)
$hintLabel.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$form.Controls.Add($hintLabel)

# Activate button
$activateBtn = New-Object System.Windows.Forms.Button
$activateBtn.Text = "Activate"
$activateBtn.Size = New-Object System.Drawing.Size(120, 38)
$activateBtn.Location = New-Object System.Drawing.Point(320, 180)
$activateBtn.BackColor = [System.Drawing.Color]::FromArgb(99, 102, 241)
$activateBtn.ForeColor = [System.Drawing.Color]::White
$activateBtn.FlatStyle = 'Flat'
$activateBtn.FlatAppearance.BorderSize = 0
$activateBtn.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$activateBtn.Cursor = 'Hand'
$activateBtn.Add_Click({
    if ($inputBox.Text.Trim() -ne "") {
        $form.Tag = $inputBox.Text.Trim()
        $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
        $form.Close()
    }
})
$form.Controls.Add($activateBtn)

# Cancel button
$cancelBtn = New-Object System.Windows.Forms.Button
$cancelBtn.Text = "Cancel"
$cancelBtn.Size = New-Object System.Drawing.Size(100, 38)
$cancelBtn.Location = New-Object System.Drawing.Point(210, 180)
$cancelBtn.BackColor = [System.Drawing.Color]::FromArgb(55, 65, 81)
$cancelBtn.ForeColor = [System.Drawing.Color]::FromArgb(209, 213, 219)
$cancelBtn.FlatStyle = 'Flat'
$cancelBtn.FlatAppearance.BorderSize = 0
$cancelBtn.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$cancelBtn.Cursor = 'Hand'
$cancelBtn.Add_Click({
    $form.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.Close()
})
$form.Controls.Add($cancelBtn)

# Handle Enter key
$form.AcceptButton = $activateBtn
$form.CancelButton = $cancelBtn

# Show dialog
$inputBox.Select()
$result = $form.ShowDialog()

if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $form.Tag
} else {
    Write-Output ""
}
