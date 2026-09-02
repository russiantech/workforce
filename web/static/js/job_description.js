document.addEventListener("DOMContentLoaded", () => {

    const jobForm = document.getElementById("jobForm");
    if (!jobForm) return;

    const jobId = jobForm.dataset.jobId;

    /* ----------------------------
       UPDATE JOB
    -----------------------------*/
    document.getElementById("saveJob")?.addEventListener("click", async () => {

        const payload = {};
        jobForm.querySelectorAll("input[name], textarea[name]").forEach(el => {
            payload[el.name] = el.value.trim();
        });

        try {
            const res = await fetch(`/job/update/${jobId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            alert(data.message || "Job updated");

        } catch (err) {
            console.error(err);
            alert("Failed to update job");
        }
    });

    /* ----------------------------
       DELETE JOB
    -----------------------------*/
    document.getElementById("deleteJob")?.addEventListener("click", async () => {
        if (!confirm("Delete this job description?")) return;

        try {
            const res = await fetch(`/job/delete/${jobId}`, { method: "DELETE" });
            const data = await res.json();

            alert(data.message || "Job deleted");
            location.reload();

        } catch (err) {
            console.error(err);
            alert("Failed to delete job");
        }
    });

    /* ----------------------------
       ADD RESPONSIBILITY
    -----------------------------*/
    document.getElementById("addResponsibility")?.addEventListener("click", async () => {

        const input = document.getElementById("newResponsibility");
        const content = input.value.trim();

        if (!content) return;

        try {
            const res = await fetch(`/job/${jobId}/responsibility`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content })
            });

            const data = await res.json();
            alert(data.message || "Responsibility added");
            location.reload();

        } catch (err) {
            console.error(err);
            alert("Failed to add responsibility");
        }
    });

    /* ----------------------------
       DELETE RESPONSIBILITY
    -----------------------------*/
    document.querySelectorAll(".remove-resp").forEach(btn => {
        btn.addEventListener("click", async () => {
            const li = btn.closest("li");
            const respId = li.dataset.respId;

            if (!confirm("Remove responsibility?")) return;

            try {
                const res = await fetch(`/responsibility/${respId}`, {
                    method: "DELETE"
                });

                const data = await res.json();
                alert(data.message || "Removed");

                li.remove();

            } catch (err) {
                console.error(err);
                alert("Failed to remove responsibility");
            }
        });
    });

});
