source("/home/wva/libpy/ml/r/report.r")

nfromtest <- function() {
  testdata = read.table("/tmp/table.txt")
  nfoldreport(testdata, dowrite=F)
}

predictreport <- function(testdata, dowrite=T) {
  if (dowrite) {write.table(testdata, "/tmp/table.txt")}
  report <- createReport()
  testdata$confbin <- confbins(testdata$conf0)
  report$byconf <- data.frame(n=tapply(testdata$confbin, testdata$confbin, length))
  addResult(report, "byconf", "N by confidence bin")

  
  report
}

confbins <- function(conf) {
  ((conf-0.00000001) %/% .05) * .05
}

testreport <- function(testdata, dowrite=T, byfold=F) {
  report <- createReport()
  d <- prepare(testdata)
  print(head(d))
  if (dowrite) {write.table(testdata, "/tmp/table.txt")}

  if (byfold) {
    report$byfold = acctable(d, d$context)
    addResult(report, "byfold", "N and Accuracy by fold")
  }
           
  bycat = acctable(d, d$report)
  report$bycat = bycat[order(-bycat$acc),]
  addResult(report, "bycat", "N and Accuracy by report category")
  
  conf <- acctable(d, d$confbin)
  report$byconf = conf
  addResult(report, "byconf", "N and Accuracy by confidence bin")

  prop = conf$n / sum(conf$n)
  max = max(c(prop, conf$acc, conf$report, conf$top5))
  max = ((max %/% 0.1) * 0.1) + 0.1
  startPlot(report, "acc", "Accuracy on 2 and 4 digits")
  x = barplot(prop, ylim=c(0,max), main="N and Accuracy by confidence", ylab="% of cases / Accuracy (%)", xlab="Confidence")
  lines(x, conf$acc)
  lines(x, conf$top5, col="red")
  lines(x, conf$report, col="blue")
  dev.off()
  
  d$confusion = sprintf("%s-%s", d$actual, d$pred0)
  t = table(d$confusion[!d$correct])
  t = t[order(-t)[1:min(10, length(t))]]
  report$confusion = data.frame( n=t)
  addResult(report, "confusion", "Top-10 confused categories")
 
  report
}

unfactor <- function(x) {as.integer(levels(x)[as.numeric(x)])}

prepare <- function(data) {
  if (!is.numeric(data$actual)) {data$actual <- unfactor(data$actual)}
  if (!is.numeric(data$pred0)) {data$pred0 <- unfactor(data$pred0)}
  #data$actual <- unfactor(data$actual)
  data <- data[!is.na(data$actual),]
  data$correct <- data$actual == data$pred0
  data$top5 <- !is.na(data$actualpos) & (data$actualpos < 5)
  data$confbin <- confbins(data$conf0)

  data$report <- data$actual %/% 100
  data$reportactual <- data$pred0 %/% 100
  data$reportcorrect <- data$report == data$reportactual
  
  data
}


acctable <- function(data, split) {
   data.frame(
    n = tapply(split, split, length),
    acc = tapply(data$correct, split, mean),              
    report = tapply(data$reportcorrect, split, mean),
    top5 = tapply(data$top5, split, mean))
 }


sample <- function(results, n=10) {
  indices = order(results$conf0)
  indices[1:min(length(results),n)]
  results[indices,"unit"]
}