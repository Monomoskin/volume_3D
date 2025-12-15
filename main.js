const fs = require("fs");
const path = require("path");

// Ruta del archivo XML de anotaciones
const xmlFilePath = "./annotations/annotations2.xml"; // Cambia esto por la ruta de tu archivo XML

// Leemos el archivo XML
fs.readFile(xmlFilePath, "utf8", (err, data) => {
  if (err) {
    console.error("Error al leer el archivo XML:", err);
    return;
  }

  // Realizamos la sustitución del nombre de archivo usando una expresión regular
  const updatedData = data.replace(/name="IMG_(\d+)\.jpeg"/g, (match, p1) => {
    return `name="Sample_${p1}_TOP.jpeg"`;
  });

  // Guardamos el archivo XML con los cambios
  fs.writeFile(xmlFilePath, updatedData, "utf8", (err) => {
    if (err) {
      console.error("Error al guardar el archivo XML:", err);
    } else {
      console.log("Archivo XML actualizado con éxito");
    }
  });
});
