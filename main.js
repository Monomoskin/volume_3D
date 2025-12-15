const fs = require("fs");
const path = require("path");

// Ruta del directorio donde están las imágenes
const directoryPath = "./IMG2"; // Cambia por la ruta de tu carpeta

// Función para cambiar los nombres de los archivos
fs.readdir(directoryPath, (err, files) => {
  if (err) {
    console.error("Error al leer el directorio:", err);
    return;
  }

  // Filtramos solo los archivos con el formato Sample_TOP_XXXX.jpeg
  files
    .filter((file) => file.match(/^Sample_TOP_\d+\.jpeg$/))
    .forEach((file) => {
      // Extraemos el número del archivo Sample_TOP_XXXX.jpeg
      const newFileName = file.replace(
        /^Sample_TOP_(\d+)\.jpeg$/,
        "Sample_$1_TOP.jpeg"
      );

      // Definir las rutas completas para el renombrado
      const oldPath = path.join(directoryPath, file);
      const newPath = path.join(directoryPath, newFileName);

      // Renombramos el archivo
      fs.rename(oldPath, newPath, (err) => {
        if (err) {
          console.error("Error al renombrar el archivo:", err);
        } else {
          console.log(`Renombrado: ${file} → ${newFileName}`);
        }
      });
    });
});
