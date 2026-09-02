$(document).ready(function() {

    /*  */
    function checkStatus() {
        fetch('/attendance_status')
            .then(response => response.json())
            .then(data => {
                const switchControl = document.getElementById('customSwitch8');
                const attendanceText = document.getElementById('attendance-text');
                if (data.status === 'signed_in') {
                    switchControl.checked = true;
                    attendanceText.textContent = 'Switch to clock out';
                } else {
                    switchControl.checked = false;
                    attendanceText.textContent = 'Switch to clock in';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('An error occurred while checking status.', 'danger');
            });
    }

    function handleAttendance(isSigningIn) {
        const action = isSigningIn ? 'signin' : 'signout';

        fetch('/create_attendance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action })
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => { throw new Error(text); });
                }
                return response.json();
            })
            .then(data => {
                //showMessage(data.message);
                //const attendanceText = document.getElementById('attendance-text');
                if (isSigningIn) {
                    //attendanceText.textContent = 'Switch to clock out';
                    showMessage(data.message, 'danger');
                } else {
                    //attendanceText.textContent = 'Switch to clock in';
                    showMessage(data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('An error occurred: ' + error.message, 'danger');
            });
    }

    function getTotalAttendance() {
        fetch('/total_attendance')
            .then(response => response.json())
            .then(data => {
                const totalAttendanceDiv = document.getElementById('totalAttendance');
                totalAttendanceDiv.textContent = `${data.total_attendance} days`;
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
    document.addEventListener("DOMContentLoaded", function() {
        getTotalAttendance();
    });
    
    function fetchAttendance() {
        // Construct full URL dynamically, supporting custom ports too
        const attendance_url = `${window.location.origin}/fetch-attendance-all`;
    
        $.ajax({
            url: attendance_url,
            method: 'GET',
            success: function(response) {
                console.log(response.attendances)
                if (response.attendances) {
                    const attendanceTableBody = $('#attendance-table-body');
                    attendanceTableBody.empty(); // Clear existing rows
    
                    response.attendances.forEach((attendance, index) => {
                        const newRow = $('#attendance-empty-row').clone();
                        newRow.removeClass('d-none');
    
                        newRow.find('td').eq(0).text(index + 1); // S/N
                        newRow.find('td').eq(1).text(attendance.user_info);
                        newRow.find('td').eq(2).text(attendance.sign_in_time);
                        newRow.find('td').eq(3).text(attendance.sign_out_time);
                        newRow.find('td').eq(4).text(attendance.date);
    
                        // Set delete button's data-id
                        newRow.find('.delete-attendance').attr("data-id", attendance.id);
    
                        attendanceTableBody.append(newRow);
                    });
                }
            },
            error: function(error) {
                console.error('Error fetching attendance:', error);
            }
        });
    }
    
    // Fetch attendance data on page load
    // fetchAttendance();
    // Optionally, fetch attendance data when a modal is opened
    $('#attendance_modal').on('show.bs.modal', function() {
        fetchAttendance();
    });
    

    // delete
    function removeAttendance(attendanceID, button) {
        const row = button.closest('tr'); // Capture the row element

        $.ajax({
            url: `/delete-attendance/${attendanceID}`,
            type: 'DELETE',
            success: function(data) {
                if (data.success) {
                    showCrudModal('Attendance deleted successfully');
                    row.remove(); // Remove the row on success
                } else {
                    showCrudModal(data.error);
                    console.error('Error deleting attendance:', data.error);
                }
            },
            error: function(xhr, status, error) {
                showCrudModal(error);
                console.error('Error:', error);
            }
        });
    }


    function removeAttendanceAll(button) {
        // Confirm the deletion action
        if (!confirm("Are you sure you want to delete all attendance records permanently?")) {
            return; // Exit if the user cancels
        }
    
        $.ajax({
            url: `/delete-all-attendance`,
            type: 'DELETE',
            success: function(data) {
                if (data.success) {
                    // Remove all rows in the attendance table
                    const tableBody = document.querySelector('#attendance-table tbody'); // Assuming the table has an ID of 'attendance-table'
                    tableBody.innerHTML = ''; // Clear the table body
    
                    showCrudModal(data.message); // Show success message
                } else {
                    showCrudModal(data.error);
                    console.error('Error deleting attendance:', data.error);
                }
            },
            error: function(xhr, status, error) {
                showCrudModal(error);
                console.error('Error:', error);
            }
        });
    }
    
    // Ensure my delete button in each row with a class 'delete-attendance'
    $(document).on('click', '.delete-attendance', function() {
        const attendanceID = $(this).data('id');
        removeAttendance(attendanceID, this);
    });
    
    // Ensure my delete all button with a class 'delete-attendance-all'
    $(document).on('click', '.delete-attendance-all', function() {
        removeAttendanceAll(this);
    });
    


});