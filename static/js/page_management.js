document.addEventListener("DOMContentLoaded", () => {
  const createPageBtn = document.getElementById("create-page-btn");
  const createPageForm = document.getElementById("create-page-form");

  // Function to handle form submission to create a vocabulary page
  createPageForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const pageName = document.getElementById("page-name").value.trim();
      const pageDescription = document.getElementById("page-description").value.trim();

      if (!pageName) {
          alert("Page name is required");
          return;
      }

      try {
          const response = await fetch("/create_vocabulary_page", {
              method: "POST",
              headers: {
                  "Content-Type": "application/json",
              },
              body: JSON.stringify({
                  page_name: pageName,
                  page_description: pageDescription,
              }),
          });

          const data = await response.json();
          if (data.status === "success") {
              alert("Page created successfully!");
              window.location.reload();
          } else {
              alert(`Error: ${data.message}`);
          }
      } catch (error) {
          console.error("Error creating page:", error);
          alert("An error occurred while creating the page. Please try again.");
      }
  });

  // Function to delete a vocabulary page
  async function deletePage(pageId) {
      if (confirm("Are you sure you want to delete this page?")) {
          try {
              const response = await fetch(`/delete_vocabulary_page/${pageId}`, {
                  method: "DELETE",
                  headers: {
                      "Content-Type": "application/json",
                  },
              });

              if (!response.ok) {
                  throw new Error(`Failed to delete page. Status: ${response.status}`);
              }

              const data = await response.json();
              if (data.status === "success") {
                  alert("Page deleted successfully!");
                  window.location.reload();
              } else {
                  alert(`Error: ${data.message}`);
              }
          } catch (error) {
              console.error("Error deleting page:", error);
              alert("An unexpected error occurred while deleting the page. Please try again.");
          }
      }
  }

  // Add event listeners for delete buttons
  document.querySelectorAll(".btn-danger").forEach((button) => {
      button.addEventListener("click", () => {
          const pageId = button.getAttribute("data-page-id");
          deletePage(pageId);
      });
  });

  // Toggle the visibility of the create page form
  createPageBtn.addEventListener("click", () => {
      if (createPageForm.style.display === "none" || createPageForm.style.display === "") {
          createPageForm.style.display = "block";
      } else {
          createPageForm.style.display = "none";
      }
  });
});